"""
Serviço de Text-to-Speech usando edge-tts (Microsoft Edge, gratuito).
Sem necessidade de API key — funciona offline via protocolo WebSocket.
"""
import asyncio
import concurrent.futures
import uuid
import logging
from pathlib import Path
import edge_tts
from ..config import settings

logger = logging.getLogger(__name__)

# Ajustes sutis de voz por emoção — valores pequenos soam mais naturais
# Ajustes grandes deixam a voz robótica/artificial
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

# Voz de fallback caso a voz especificada não exista
FALLBACK_VOICE = "pt-BR-FranciscaNeural"


def _prepare_text(text: str) -> str:
    """
    Limpa e prepara o texto para TTS.
    Remove múltiplos espaços/quebras que causam pausas artificiais.
    Normaliza travessões de diálogo para leitura fluida.
    """
    import re

    # Normaliza travessões de diálogo: — texto → texto (remove o travessão inicial)
    # O TTS lê melhor sem o travessão, que causa uma pausa artificial
    text = re.sub(r'^—\s*', '', text.strip())
    text = re.sub(r'\n—\s*', '\n', text)

    # Remove múltiplas quebras de linha (causam silêncios)
    text = re.sub(r'\n{2,}', ' ', text)
    text = re.sub(r'\n', ' ', text)

    # Remove espaços múltiplos
    text = re.sub(r' {2,}', ' ', text)

    # Remove travessões no meio do texto que causam pausas (— disse X)
    # Mantém o conteúdo mas remove o travessão
    text = re.sub(r'\s*—\s*', ' — ', text)

    return text.strip()


async def _generate_async(text: str, voice: str, rate: str, pitch: str, output_path: str) -> None:
    """Coroutine que gera o áudio via edge-tts."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


def _run_coroutine(coro):
    """Executa uma coroutine de forma segura em qualquer contexto (sync ou async)."""
    try:
        loop = asyncio.get_running_loop()
        # Estamos dentro de um loop — executa em thread separada
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # Nenhum loop rodando — executa diretamente
        return asyncio.run(coro)


def generate_audio(
    text: str,
    voice_id: str,
    emotion: str = "neutral",
    output_dir: Path | None = None,
) -> tuple[str, float]:
    """
    Gera áudio MP3 para o texto usando edge-tts.
    Retorna (caminho_do_arquivo, duração_estimada_segundos).
    """
    params = EMOTION_SETTINGS.get(emotion, EMOTION_SETTINGS["neutral"])
    dest_dir = output_dir or settings.audio_path
    filename = f"{uuid.uuid4().hex}.mp3"
    dest = str(dest_dir / filename)

    # Prepara o texto para evitar pausas artificiais
    clean_text = _prepare_text(text)
    if not clean_text:
        clean_text = text.strip()

    try:
        _run_coroutine(
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

    except Exception as e:
        logger.warning(f"Erro edge-tts (voice={voice_id}): {e}. Tentando fallback...")
        try:
            _run_coroutine(
                _generate_async(
                    text=clean_text,
                    voice=FALLBACK_VOICE,
                    rate="+0%",
                    pitch="+0Hz",
                    output_path=dest,
                )
            )
            words = len(text.split())
            return dest, round((words / 150) * 60, 2)
        except Exception as e2:
            logger.error(f"Fallback TTS também falhou: {e2}")
            raise


def estimate_duration(text: str, speed: float = 1.0) -> float:
    """Estima duração em segundos com base no número de palavras."""
    words = len(text.split())
    return round((words / 150) * 60 * (1 / speed), 2)


async def list_available_voices_async() -> list[dict]:
    """Lista todas as vozes disponíveis no edge-tts."""
    voices = await edge_tts.list_voices()
    return [{"id": v["ShortName"], "name": v["FriendlyName"], "locale": v["Locale"]} for v in voices]


def list_available_voices() -> list[dict]:
    """Versão síncrona de list_available_voices_async."""
    return _run_coroutine(list_available_voices_async())
