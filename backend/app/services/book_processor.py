"""
Orquestrador do processamento completo de um livro — LÓGICA RÁDIO-NOVELA.
Cada bloco de fala/narração é processado individualmente com a voz correta.
TTS gerado em paralelo (lotes de 5) para performance.
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
from ..services.tts_service import generate_audio_batch, estimate_duration
from ..config import settings

logger = logging.getLogger(__name__)

CHAR_COLORS = [
    "#7C3AED", "#2563EB", "#059669", "#DC2626",
    "#D97706", "#DB2777", "#0891B2", "#65A30D",
    "#9333EA", "#6366F1",
]

MAX_PROCESSING_SECONDS = 7200  # 2 horas
TTS_BATCH_SIZE = 20  # segmentos por lote de TTS paralelo


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

        # Se arquivo sumiu do disco (Render reiniciou), restaura do banco
        file_path = book.file_path
        if not Path(file_path).exists():
            if book.file_content:
                logger.info(f"[Livro {book_id}] Arquivo ausente — restaurando do banco de dados")
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                Path(file_path).write_bytes(book.file_content)
            else:
                raise FileNotFoundError(
                    "Arquivo não encontrado e sem backup no banco. "
                    "Por favor, envie o arquivo novamente."
                )

        # Extrai texto com timeout de 90s (PDFs complexos podem travar)
        import concurrent.futures as _cf
        with _cf.ThreadPoolExecutor(max_workers=1) as _pool:
            _fut = _pool.submit(extract_text, file_path, book.format)
            try:
                raw_text = _fut.result(timeout=90)
            except _cf.TimeoutError:
                raise TimeoutError("Extração de texto excedeu 90s. O arquivo pode estar corrompido.")
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
            from ..services.narrative_analyzer import _heuristic_with_context
            analyses = []
            for i, block in enumerate(blocks):
                prev = blocks[i-1] if i > 0 else None
                nxt = blocks[i+1] if i < len(blocks)-1 else None
                result = _heuristic_with_context(block, prev, nxt, character_names)
                analyses.append(result or {"character_name": "Narrador", "emotion": "neutral"})

        from collections import Counter
        dist = Counter(a["character_name"] for a in analyses)
        logger.info(f"[Livro {book_id}] Distribuição de falas: {dict(dist)}")

        # ── 5. Geração de áudio em paralelo (lotes de TTS_BATCH_SIZE) ────
        _update_status(db, book, "generating_audio", f"Gerando áudio... 0/{total_blocks}", 38)
        total_duration = 0.0
        failed_segments = 0

        # Prepara todos os segmentos
        seg_meta = []
        for block, analysis in zip(blocks, analyses):
            char_name = analysis.get("character_name", "Narrador")
            char = char_map.get(char_name, narrator)
            emotion = analysis.get("emotion", "neutral")
            seg_meta.append({
                "block": block,
                "char": char,
                "char_name": char_name,
                "emotion": emotion,
            })

        # Processa em lotes paralelos
        audio_results: list[tuple] = []  # (path_or_None, duration)

        for batch_start in range(0, total_blocks, TTS_BATCH_SIZE):
            if time.time() - start_time > MAX_PROCESSING_SECONDS:
                logger.error(f"Livro {book_id} excedeu tempo máximo. Encerrando.")
                # Preenche restantes com None
                remaining = total_blocks - len(audio_results)
                audio_results.extend([(None, 0.0)] * remaining)
                break

            batch = seg_meta[batch_start:batch_start + TTS_BATCH_SIZE]
            tts_inputs = []
            for m in batch:
                char = m["char"]
                tts_inputs.append({
                    "text": m["block"],
                    "voice_id": char.voice_id if char else None,
                    "emotion": m["emotion"],
                    "context_text": "",
                })

            batch_results = generate_audio_batch(tts_inputs)
            audio_results.extend(batch_results)

            # Atualiza progresso após cada lote
            done = min(batch_start + TTS_BATCH_SIZE, total_blocks)
            progress = 38 + int((done / total_blocks) * 57)
            _update_status(
                db, book, "generating_audio",
                f"Gerando áudio... {done}/{total_blocks}",
                progress,
            )
            db.commit()
            logger.info(f"[Livro {book_id}] Lote TTS {batch_start}-{done} concluído")

        # Persiste segmentos no banco
        for idx, (meta, (audio_path, duration)) in enumerate(zip(seg_meta, audio_results)):
            if audio_path is None:
                failed_segments += 1
                duration = estimate_duration(meta["block"])

            char = meta["char"]
            seg = AudioSegment(
                book_id=book_id,
                character_id=char.id if char else None,
                segment_index=idx,
                text=meta["block"],
                emotion=meta["emotion"],
                audio_path=audio_path,
                duration=duration,
                status="ready" if audio_path else "pending",
            )
            db.add(seg)
            total_duration += duration

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

        # Deleta áudios antigos
        for seg in segments:
            if seg.audio_path:
                Path(seg.audio_path).unlink(missing_ok=True)

        # Prepara inputs TTS
        tts_inputs = []
        for seg in segments:
            char = characters.get(seg.character_id)
            tts_inputs.append({
                "text": seg.text,
                "voice_id": char.voice_id if char else None,
                "emotion": seg.emotion or "neutral",
            })

        # Gera em lotes paralelos
        all_results = []
        for batch_start in range(0, total, TTS_BATCH_SIZE):
            batch = tts_inputs[batch_start:batch_start + TTS_BATCH_SIZE]
            batch_results = generate_audio_batch(batch)
            all_results.extend(batch_results)

            done = min(batch_start + TTS_BATCH_SIZE, total)
            progress = int((done / max(total, 1)) * 100)
            _update_status(db, book, "generating_audio",
                           f"Regenerando... {done}/{total}", progress)
            db.commit()

        total_duration = 0.0
        for seg, (audio_path, duration) in zip(segments, all_results):
            if audio_path is None:
                duration = estimate_duration(seg.text)
            seg.audio_path = audio_path
            seg.duration = duration
            seg.status = "ready" if audio_path else "pending"
            total_duration += duration

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
