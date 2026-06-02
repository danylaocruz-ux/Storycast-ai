"""
Serviço de Text-to-Speech usando edge-tts (Microsoft Edge, gratuito).
Sem necessidade de API key — funciona via protocolo WebSocket.
"""
import asyncio
import concurrent.futures
import uuid
import logging
from pathlib import Path
import edge_tts
from ..config import settings

logger = logging.getLogger(__name__)

# Timeout por chamada TTS (segundos) — edge-tts pode travar sem timeout
TTS_TIMEOUT = 45

EMOTION_SETTINGS: dict[str, dict] = {
    "neutral":     {"rate": "+0%",  "pitch": "+0Hz",  "speed": 1.0},
    "happy":       {"rate": "+5%",  "pitch": "+2Hz",  "speed": 1.05},
    "sad":         {"rate": "-8%",  "pitch": "-3Hz",  "speed": 0.95},
    "angry":       {"rate": "+8%",  "pitch": "+2Hz",  "speed": 1.05},
    "fearful":     {"rate": "+3%",  "pitch": "+1Hz",  "speed": 1.02},
    "surprised":   {"rate": "+5%",  "pitch": "+3Hz",  "speed": 1.03},
    "romantic":    {"rate": "-5%",  "pitch": "-1Hz",  "speed": 0.97},
    "suspenseful": {"rate": "-3%",  "pitch": "+0Hz",  "speed": 0.98},
}

FALLBACK_VOICE = "pt-BR-FranciscaNeural"


def _prepare_text(text: str) -> str:
    import re
    text = re.sub(r'^—\s*', '', text.strip())
    text = re.sub(r'\n—\s*', '\n', text)
    text = re.sub(r'\n{2,}', ' ', text)
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\s*—\s*', ' — ', text)
    return text.strip()


async def _generate_async(text: str, voice: str, rate: str, pitch: str, output_path: str) -> None:
    """Gera áudio com timeout embutido para evitar trava."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await asyncio.wait_for(communicate.save(output_path), timeout=TTS_TIMEOUT)


def _run_in_new_thread(coro, timeout: float = TTS_TIMEOUT + 5) -> None:
    """
    Executa uma coroutine em uma thread dedicada com timeout total.
    Garante que nunca trava indefinidamente.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        # timeout externo como segunda camada de proteção
        future.result(timeout=timeout)


def generate_audio(
    text: str,
    voice_id: str,
    emotion: str = "neutral",
    output_dir: Path | None = None,
) -> tuple[str, float]:
    """
    Gera áudio MP3 com timeout — nunca trava por mais de TTS_TIMEOUT segundos.
    Retorna (caminho_do_arquivo, duração_estimada_segundos).
    """
    params = EMOTION_SETTINGS.get(emotion, EMOTION_SETTINGS["neutral"])
    dest_dir = output_dir or settings.audio_path
    filename = f"{uuid.uuid4().hex}.mp3"
    dest = str(dest_dir / filename)

    clean_text = _prepare_text(text)
    if not clean_text:
        clean_text = text.strip()
    # Trunca textos muito longos que podem causar timeout
    if len(clean_text) > 2000:
        clean_text = clean_text[:2000]

    try:
        _run_in_new_thread(
            _generate_async(
                text=clean_text,
                voice=voice_id or FALLBACK_VOICE,
                rate=params["rate"],
                pitch=params["pitch"],
                output_path=dest,
            )
        )
        words = len(text.split())
        duration = (words / 150) * 60 * (1 / params["speed"])
        return dest, round(duration, 2)

    except (concurrent.futures.TimeoutError, asyncio.TimeoutError, TimeoutError) as e:
        logger.warning(f"TTS timeout ({TTS_TIMEOUT}s) voice={voice_id}. Tentando fallback...")
        # Remove arquivo parcial se existir
        Path(dest).unlink(missing_ok=True)
        filename2 = f"{uuid.uuid4().hex}.mp3"
        dest2 = str(dest_dir / filename2)
        try:
            _run_in_new_thread(
                _generate_async(
                    text=clean_text[:800],  # texto menor para fallback
                    voice=FALLBACK_VOICE,
                    rate="+0%",
                    pitch="+0Hz",
                    output_path=dest2,
                ),
                timeout=30,
            )
            words = len(clean_text[:800].split())
            return dest2, round((words / 150) * 60, 2)
        except Exception as e2:
            logger.error(f"Fallback TTS também falhou (timeout/erro): {e2}")
            raise

    except Exception as e:
        logger.warning(f"Erro edge-tts (voice={voice_id}): {e}. Tentando fallback...")
        Path(dest).unlink(missing_ok=True)
        filename2 = f"{uuid.uuid4().hex}.mp3"
        dest2 = str(dest_dir / filename2)
        try:
            _run_in_new_thread(
                _generate_async(
                    text=clean_text,
                    voice=FALLBACK_VOICE,
                    rate="+0%",
                    pitch="+0Hz",
                    output_path=dest2,
                ),
                timeout=30,
            )
            words = len(text.split())
            return dest2, round((words / 150) * 60, 2)
        except Exception as e2:
            logger.error(f"Fallback TTS também falhou: {e2}")
            raise


def estimate_duration(text: str, speed: float = 1.0) -> float:
    words = len(text.split())
    return round((words / 150) * 60 * (1 / speed), 2)


async def list_available_voices_async() -> list[dict]:
    voices = await edge_tts.list_voices()
    return [{"id": v["ShortName"], "name": v["FriendlyName"], "locale": v["Locale"]} for v in voices]


def list_available_voices() -> list[dict]:
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, list_available_voices_async())
            return future.result(timeout=15)
    except Exception:
        return []
