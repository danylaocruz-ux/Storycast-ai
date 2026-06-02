"""
Orquestrador do processamento completo de um livro — LÓGICA RÁDIO-NOVELA.
Cada bloco de fala/narração é processado individualmente com a voz correta.
"""
import logging
import threading
import time
import requests
from pathlib import Path
from sqlalchemy.orm import Session
from ..models.book import Book
from ..models.character import Character
from ..models.audio_segment import AudioSegment
from ..services.text_extractor import (
    extract_text, clean_text, split_into_speaker_blocks, detect_language
)
from ..services.narrative_analyzer import extract_characters, analyze_segments_batch
from ..services.voice_assigner import assign_voice
from ..services.tts_service import generate_audio, estimate_duration
from ..config import settings

logger = logging.getLogger(__name__)

CHAR_COLORS = [
    "#7C3AED", "#2563EB", "#059669", "#DC2626",
    "#D97706", "#DB2777", "#0891B2", "#65A30D",
    "#9333EA", "#6366F1",
]

MAX_PROCESSING_SECONDS = 7200  # 2 horas


def _keep_alive_ping():
    """Evita que o Render free tier durma durante o processamento."""
    base_url = getattr(settings, 'SERVICE_URL', None) or 'http://localhost:8000'
    url = f"{base_url.rstrip('/')}/health"
    while True:
        time.sleep(600)
        try:
            requests.get(url, timeout=10)
            logger.info("Keep-alive ping OK")
        except Exception as e:
            logger.warning(f"Keep-alive falhou: {e}")


def process_book(book_id: int, db: Session) -> None:
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return

    threading.Thread(target=_keep_alive_ping, daemon=True).start()
    start_time = time.time()

    try:
        # ── 1. Extração de texto ─────────────────────────────────────────
        _update_status(db, book, "extracting", "Extraindo texto...", 5)
        raw_text = extract_text(book.file_path, book.format)
        text = clean_text(raw_text)
        language = detect_language(text)
        book.language = language
        book.total_chars = len(text)
        db.commit()

        # ── 2. Segmentação por falante ────────────────────────────────────
        _update_status(db, book, "analyzing", "Segmentando por personagens...", 12)
        blocks = split_into_speaker_blocks(text, max_narrative_chars=500)
        total_blocks = len(blocks)
        logger.info(f"[Livro {book_id}] {total_blocks} blocos de fala/narração")

        # ── 3. Identificação de personagens ──────────────────────────────
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
                age_group=cd.get("age_group", "adult"),
                personality=cd.get("personality", "other"),
                is_narrator=cd.get("is_narrator", False),
                used_voice_ids=used_voice_ids,
            )
            used_voice_ids.add(voice["id"])
            char = Character(
                book_id=book_id,
                name=cd["name"],
                description=cd.get("description"),
                gender=cd.get("gender", "neutral"),
                age_group=cd.get("age_group", "adult"),
                personality=cd.get("personality"),
                is_narrator=cd.get("is_narrator", False),
                voice_id=voice["id"],
                voice_name=voice["name"],
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

        # ── 4. Análise de falantes (rádio-novela) ─────────────────────────
        _update_status(db, book, "analyzing", "Atribuindo falas aos personagens...", 32)
        if settings.GROQ_API_KEY:
            analyses = analyze_segments_batch(blocks, character_names, batch_size=8)
        else:
            # Sem LLM: usa heurística básica
            from ..services.narrative_analyzer import _heuristic_with_context, _is_dialogue
            analyses = []
            for i, block in enumerate(blocks):
                prev = blocks[i-1] if i > 0 else None
                nxt = blocks[i+1] if i < len(blocks)-1 else None
                result = _heuristic_with_context(block, prev, nxt, character_names)
                analyses.append(result or {"character_name": "Narrador", "emotion": "neutral"})

        # Log resumo da distribuição de falas
        from collections import Counter
        dist = Counter(a["character_name"] for a in analyses)
        logger.info(f"[Livro {book_id}] Distribuição de falas: {dict(dist)}")

        # ── 5. Geração de áudio por falante ──────────────────────────────
        _update_status(db, book, "generating_audio", f"Gerando áudio... 0/{total_blocks}", 38)
        total_duration = 0.0
        failed_segments = 0

        for idx, (block, analysis) in enumerate(zip(blocks, analyses)):
            if time.time() - start_time > MAX_PROCESSING_SECONDS:
                logger.error(f"Livro {book_id} excedeu tempo máximo. Encerrando.")
                break

            char_name = analysis.get("character_name", "Narrador")
            char = char_map.get(char_name, narrator)
            emotion = analysis.get("emotion", "neutral")

            audio_path = None
            duration = estimate_duration(block)

            if char and char.voice_id:
                try:
                    audio_path, duration = generate_audio(
                        text=block,
                        voice_id=char.voice_id,
                        emotion=emotion,
                    )
                    logger.debug(
                        f"[{idx}/{total_blocks}] {char_name} ({char.voice_name}): "
                        f"{block[:50]}..."
                    )
                except Exception as e:
                    failed_segments += 1
                    logger.warning(f"TTS falhou no segmento {idx} ({char_name}): {e}")

            seg = AudioSegment(
                book_id=book_id,
                character_id=char.id if char else None,
                segment_index=idx,
                text=block,
                emotion=emotion,
                audio_path=audio_path,
                duration=duration,
                status="ready" if audio_path else "pending",
            )
            db.add(seg)
            total_duration += duration

            if idx % 5 == 0:
                progress = 38 + int((idx / total_blocks) * 57)
                _update_status(
                    db, book, "generating_audio",
                    f"Gerando áudio... {idx}/{total_blocks}",
                    progress,
                )
                db.commit()

        book.total_segments = total_blocks
        book.total_duration = total_duration
        db.commit()

        if failed_segments == total_blocks:
            _update_status(db, book, "error",
                           "Todos os segmentos falharam no TTS. Verifique a conexão.", 0)
        else:
            msg = f"Pronto! {total_blocks} blocos processados"
            if failed_segments:
                msg += f" ({failed_segments} sem áudio)"
            _update_status(db, book, "ready", msg, 100)

    except Exception as e:
        logger.error(f"Erro ao processar livro {book_id}: {e}", exc_info=True)
        _update_status(db, book, "error", str(e)[:200], book.progress)


def regenerate_audio(book_id: int, db: Session) -> None:
    """Re-gera apenas o TTS mantendo os falantes já atribuídos."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        return

    threading.Thread(target=_keep_alive_ping, daemon=True).start()

    try:
        segments = (
            db.query(AudioSegment)
            .filter(AudioSegment.book_id == book_id)
            .order_by(AudioSegment.segment_index)
            .all()
        )
        characters = {c.id: c for c in
                      db.query(Character).filter(Character.book_id == book_id).all()}
        total = len(segments)

        _update_status(db, book, "generating_audio", "Regenerando áudio com novas vozes...", 0)
        total_duration = 0.0

        for idx, seg in enumerate(segments):
            char = characters.get(seg.character_id)
            if seg.audio_path:
                Path(seg.audio_path).unlink(missing_ok=True)

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
                progress = int((idx / max(total, 1)) * 100)
                _update_status(db, book, "generating_audio",
                               f"Regenerando... {idx}/{total}", progress)
                db.commit()

        book.total_duration = total_duration
        _update_status(db, book, "ready", "Áudio regenerado com sucesso!", 100)

    except Exception as e:
        logger.error(f"Erro ao regenerar áudio: {e}", exc_info=True)
        _update_status(db, book, "error", str(e)[:200], book.progress)


def _update_status(db, book, status, message, progress):
    book.status = status
    book.status_message = message
    book.progress = progress
    db.commit()
    logger.info(f"[Livro {book.id}] {status} ({progress}%) — {message}")


def _default_narrator_data():
    return {
        "name": "Narrador", "description": "Voz narrativa", "gender": "neutral",
        "age_group": "adult", "personality": "narrator", "is_narrator": True,
        "appearance_order": 0,
    }
