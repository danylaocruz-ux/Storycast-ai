"""
Orquestrador do processamento completo de um livro.
Pipeline: extração → análise → personagens → TTS (edge-tts, gratuito)
"""
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from ..models.book import Book
from ..models.character import Character
from ..models.audio_segment import AudioSegment
from ..services.text_extractor import extract_text, clean_text, split_into_chunks, detect_language
from ..services.narrative_analyzer import extract_characters, analyze_segments_batch
from ..services.voice_assigner import assign_voice
from ..services.tts_service import generate_audio, estimate_duration
from ..config import settings

logger = logging.getLogger(__name__)

CHAR_COLORS = [
    "#7C3AED", "#2563EB", "#059669", "#DC2626",
    "#D97706", "#DB2777", "#0891B2", "#65A30D",
    "#7C3AED", "#6366F1",
]


def process_book(book_id: int, db: Session) -> None:
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return

    try:
        _update_status(db, book, "extracting", "Extraindo texto...", 5)
        raw_text = extract_text(book.file_path, book.format)
        text = clean_text(raw_text)
        language = detect_language(text)
        book.language = language
        book.total_chars = len(text)
        db.commit()

        _update_status(db, book, "analyzing", "Dividindo em segmentos...", 15)
        chunks = split_into_chunks(text, max_chars=600)

        _update_status(db, book, "analyzing", "Identificando personagens...", 20)
        if settings.GROQ_API_KEY:
            char_data = extract_characters(text)
        else:
            char_data = [_default_narrator_data()]

        char_map: dict[str, Character] = {}
        used_voice_ids: set[str] = set()

        for i, cd in enumerate(char_data):
            voice = assign_voice(
                name=cd["name"], gender=cd.get("gender", "neutral"),
                age_group=cd.get("age_group", "adult"), personality=cd.get("personality", "other"),
                is_narrator=cd.get("is_narrator", False), used_voice_ids=used_voice_ids,
            )
            used_voice_ids.add(voice["id"])
            char = Character(
                book_id=book_id, name=cd["name"], description=cd.get("description"),
                gender=cd.get("gender", "neutral"), age_group=cd.get("age_group", "adult"),
                personality=cd.get("personality"), is_narrator=cd.get("is_narrator", False),
                voice_id=voice["id"], voice_name=voice["name"],
                appearance_order=cd.get("appearance_order", i),
                color=CHAR_COLORS[i % len(CHAR_COLORS)],
            )
            db.add(char)
            db.flush()
            char_map[cd["name"]] = char

        db.commit()
        character_names = list(char_map.keys())
        narrator = next((c for c in char_map.values() if c.is_narrator), None)
        if narrator is None and char_map:
            narrator = list(char_map.values())[0]

        _update_status(db, book, "analyzing", "Analisando narrativa...", 35)
        if settings.GROQ_API_KEY:
            analyses = analyze_segments_batch(chunks, character_names, batch_size=15)
        else:
            analyses = [{"character_name": "Narrador", "emotion": "neutral"}] * len(chunks)

        _update_status(db, book, "generating_audio", "Gerando áudio...", 40)
        total_duration = 0.0

        for idx, (chunk, analysis) in enumerate(zip(chunks, analyses)):
            char_name = analysis.get("character_name", "Narrador")
            char = char_map.get(char_name, narrator)
            emotion = analysis.get("emotion", "neutral")

            audio_path = None
            duration = estimate_duration(chunk)
            if char and char.voice_id:
                try:
                    audio_path, duration = generate_audio(text=chunk, voice_id=char.voice_id, emotion=emotion)
                except Exception as e:
                    logger.warning(f"Falha TTS segmento {idx}: {e}")

            seg = AudioSegment(
                book_id=book_id, character_id=char.id if char else None,
                segment_index=idx, text=chunk, emotion=emotion,
                audio_path=audio_path, duration=duration,
                status="ready" if audio_path else "pending",
            )
            db.add(seg)
            total_duration += duration

            if idx % 10 == 0:
                progress = 40 + int((idx / len(chunks)) * 55)
                _update_status(db, book, "generating_audio", f"Gerando áudio... {idx}/{len(chunks)}", progress)
                db.commit()

        book.total_segments = len(chunks)
        book.total_duration = total_duration
        db.commit()
        _update_status(db, book, "ready", "Processamento concluído!", 100)

    except Exception as e:
        logger.error(f"Erro ao processar livro {book_id}: {e}", exc_info=True)
        _update_status(db, book, "error", str(e), book.progress)


def regenerate_audio(book_id: int, db: Session) -> None:
    """Re-gera apenas o TTS usando as vozes atuais dos personagens."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return

    try:
        segments = (
            db.query(AudioSegment)
            .filter(AudioSegment.book_id == book_id)
            .order_by(AudioSegment.segment_index)
            .all()
        )
        characters = {c.id: c for c in db.query(Character).filter(Character.book_id == book_id).all()}

        _update_status(db, book, "generating_audio", "Regenerando áudio com novas vozes...", 0)
        total_duration = 0.0

        for idx, seg in enumerate(segments):
            char = characters.get(seg.character_id)

            # Remove arquivo de áudio antigo
            if seg.audio_path:
                try:
                    Path(seg.audio_path).unlink(missing_ok=True)
                except Exception:
                    pass

            audio_path = None
            duration = estimate_duration(seg.text)

            if char and char.voice_id:
                try:
                    audio_path, duration = generate_audio(
                        text=seg.text,
                        voice_id=char.voice_id,
                        emotion=seg.emotion or "neutral",
                    )
                except Exception as e:
                    logger.warning(f"Falha TTS segmento {idx}: {e}")

            seg.audio_path = audio_path
            seg.duration = duration
            seg.status = "ready" if audio_path else "pending"
            total_duration += duration

            if idx % 5 == 0:
                progress = int((idx / max(len(segments), 1)) * 100)
                _update_status(db, book, "generating_audio",
                               f"Regenerando... {idx}/{len(segments)}", progress)
                db.commit()

        book.total_duration = total_duration
        _update_status(db, book, "ready", "Áudio regenerado com sucesso!", 100)

    except Exception as e:
        logger.error(f"Erro ao regenerar áudio do livro {book_id}: {e}", exc_info=True)
        _update_status(db, book, "error", str(e), book.progress)


def _update_status(db, book, status, message, progress):
    book.status = status
    book.status_message = message
    book.progress = progress
    db.commit()
    logger.info(f"[Livro {book.id}] {status} ({progress}%) — {message}")


def _default_narrator_data():
    return {"name": "Narrador", "description": "Voz narrativa", "gender": "neutral",
            "age_group": "adult", "personality": "narrator", "is_narrator": True, "appearance_order": 0}
