"""
Serviço de Text-to-Speech.
Usa ElevenLabs para gerar áudio com múltiplas vozes.
Adaptação emocional via stability/similarity_boost.
"""
import uuid
import logging
from pathlib import Path
from elevenlabs import ElevenLabs, VoiceSettings
from ..config import settings

logger = logging.getLogger(__name__)

# ── Mapeamento emoção → parâmetros de voz ────────────────────────────────────
EMOTION_SETTINGS: dict[str, dict] = {
    "neutral":     {"stability": 0.75, "similarity_boost": 0.75, "style": 0.0,  "speed": 1.0},
    "happy":       {"stability": 0.50, "similarity_boost": 0.80, "style": 0.3,  "speed": 1.1},
    "sad":         {"stability": 0.85, "similarity_boost": 0.70, "style": 0.1,  "speed": 0.9},
    "angry":       {"stability": 0.40, "similarity_boost": 0.85, "style": 0.6,  "speed": 1.15},
    "fearful":     {"stability": 0.55, "similarity_boost": 0.75, "style": 0.4,  "speed": 1.05},
    "surprised":   {"stability": 0.45, "similarity_boost": 0.80, "style": 0.5,  "speed": 1.1},
    "romantic":    {"stability": 0.80, "similarity_boost": 0.70, "style": 0.2,  "speed": 0.95},
    "suspenseful": {"stability": 0.65, "similarity_boost": 0.75, "style": 0.35, "speed": 0.98},
}


def generate_audio(
    text: str,
    voice_id: str,
    emotion: str = "neutral",
    output_dir: Path | None = None,
) -> tuple[str, float]:
    """
    Gera áudio para o texto com a voz e emoção especificadas.
    Retorna (caminho_do_arquivo, duracao_estimada_segundos).
    """
    if not settings.ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY não configurada")

    params = EMOTION_SETTINGS.get(emotion, EMOTION_SETTINGS["neutral"])
    dest_dir = output_dir or settings.audio_path
    filename = f"{uuid.uuid4().hex}.mp3"
    dest = dest_dir / filename

    el = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)

    try:
        audio_bytes = el.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=params["stability"],
                similarity_boost=params["similarity_boost"],
                style=params["style"],
                use_speaker_boost=True,
            ),
        )
        # Coleta o gerador em bytes
        audio_data = b"".join(audio_bytes) if hasattr(audio_bytes, "__iter__") else audio_bytes
        dest.write_bytes(audio_data)

        # Estimativa de duração: ~150 palavras/minuto para audio médio
        words = len(text.split())
        duration = (words / 150) * 60 * (1 / params["speed"])

        return str(dest), round(duration, 2)

    except Exception as e:
        logger.error(f"Erro TTS (voice={voice_id}, emotion={emotion}): {e}")
        raise


def estimate_duration(text: str, speed: float = 1.0) -> float:
    """Estima duração em segundos com base no número de palavras."""
    words = len(text.split())
    return round((words / 150) * 60 * (1 / speed), 2)
