"""
Serviço de Text-to-Speech com expressão emocional.
Usa edge-tts (Microsoft) com ajustes de prosódia por emoção.
Geração em paralelo (até 5 simultâneos) para performance.
"""
import asyncio
import concurrent.futures
import re
import uuid
import logging
from pathlib import Path
from typing import Optional
import edge_tts
from ..config import settings

logger = logging.getLogger(__name__)

TTS_TIMEOUT = 20        # segundos por chamada (reduzido de 45)
TTS_CONCURRENCY = 5     # chamadas simultâneas máximas

# ── Configurações emocionais expressivas ──────────────────────────────────────
EMOTION_SETTINGS: dict[str, dict] = {
    "neutral":      {"rate": "+0%",   "pitch": "+0Hz",   "volume": "+0%"},
    "happy":        {"rate": "+18%",  "pitch": "+5Hz",   "volume": "+5%"},
    "excited":      {"rate": "+25%",  "pitch": "+8Hz",   "volume": "+10%"},
    "sad":          {"rate": "-20%",  "pitch": "-6Hz",   "volume": "-5%"},
    "angry":        {"rate": "+22%",  "pitch": "+6Hz",   "volume": "+15%"},
    "fearful":      {"rate": "+15%",  "pitch": "+4Hz",   "volume": "-8%"},
    "surprised":    {"rate": "+20%",  "pitch": "+10Hz",  "volume": "+8%"},
    "romantic":     {"rate": "-12%",  "pitch": "-3Hz",   "volume": "-5%"},
    "suspenseful":  {"rate": "-15%",  "pitch": "-3Hz",   "volume": "-10%"},
    "whispering":   {"rate": "-18%",  "pitch": "-5Hz",   "volume": "-15%"},
    "crying":       {"rate": "-25%",  "pitch": "-8Hz",   "volume": "-8%"},
    "shouting":     {"rate": "+28%",  "pitch": "+8Hz",   "volume": "+20%"},
}

FALLBACK_VOICE = "pt-BR-FranciscaNeural"

# ── Detecção de emoção por heurística ────────────────────────────────────────
_EMOTION_VERBS: dict[str, list[str]] = {
    "angry":       ["gritou", "berrou", "rosnou", "replicou irritado", "disse com raiva",
                    "explodiu", "vociferou", "resmungou", "protestou"],
    "sad":         ["chorou", "soluçou", "lamentou", "gemeu", "disse com tristeza",
                    "murmurou triste", "suspirou fundo"],
    "happy":       ["riu", "gargalhou", "exclamou alegre", "disse animado",
                    "comemorou", "festejou"],
    "fearful":     ["tremeu", "gaguejou", "disse assustado", "murmurou com medo",
                    "sussurrou apavorado"],
    "surprised":   ["exclamou", "disse surpreso", "ficou boquiaberto", "não acreditou"],
    "romantic":    ["sussurrou carinhoso", "disse suavemente", "cochicho amoroso",
                    "falou com ternura"],
    "suspenseful": ["pausou", "hesitou", "disse devagar", "olhou ao redor"],
    "whispering":  ["sussurrou", "cochichou", "murmurou baixinho"],
    "crying":      ["disse entre lágrimas", "falou chorando", "soluçou"],
    "shouting":    ["gritou alto", "berrou com toda força", "vociferou"],
}

_PUNCT_EMOTION: list[tuple[str, str]] = [
    (r"!{2,}", "angry"),
    (r"\?{2,}", "surprised"),
    (r"\.{3,}", "suspenseful"),
    (r"!\?", "surprised"),
]


def detect_emotion_from_text(text: str, context_text: str = "") -> str:
    combined = (text + " " + context_text).lower()
    for emotion, verbs in _EMOTION_VERBS.items():
        for verb in verbs:
            if verb in combined:
                return emotion
    for pattern, emotion in _PUNCT_EMOTION:
        if re.search(pattern, text):
            return emotion
    return "neutral"


# ── Preparação de texto ───────────────────────────────────────────────────────
def _prepare_text(text: str) -> str:
    text = re.sub(r'^[—–]\s*', '', text.strip())
    text = re.sub(r'\n{2,}', ' ', text)
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\.{4,}', '...', text)
    text = re.sub(
        r'\s*[—–]\s*(disse|falou|respondeu|perguntou|exclamou|murmurou|gritou|sussurrou)\s+\w+.*$',
        '', text, flags=re.IGNORECASE
    )
    return text.strip()


# ── Core async TTS ────────────────────────────────────────────────────────────
async def _generate_one_async(
    text: str, voice: str, rate: str, pitch: str, volume: str,
    output_path: str, semaphore: asyncio.Semaphore
) -> bool:
    """Gera um arquivo de áudio. Retorna True se ok, False se falhou."""
    async with semaphore:
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
            await asyncio.wait_for(communicate.save(output_path), timeout=TTS_TIMEOUT)
            return True
        except Exception as e:
            logger.warning(f"TTS falhou (voice={voice}): {type(e).__name__}: {e}")
            Path(output_path).unlink(missing_ok=True)
            return False


async def _generate_batch_async(items: list[dict]) -> list[Optional[str]]:
    """
    Gera múltiplos áudios em paralelo com semáforo de concorrência.
    items: lista de dicts com keys: text, voice, rate, pitch, volume, output_path
    Retorna lista de paths (None se falhou).
    """
    semaphore = asyncio.Semaphore(TTS_CONCURRENCY)
    tasks = [
        _generate_one_async(
            text=it["text"],
            voice=it["voice"],
            rate=it["rate"],
            pitch=it["pitch"],
            volume=it["volume"],
            output_path=it["output_path"],
            semaphore=semaphore,
        )
        for it in items
    ]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return [items[i]["output_path"] if ok else None for i, ok in enumerate(results)]


def generate_audio_batch(
    segments: list[dict],
    dest_dir: Optional[Path] = None,
) -> list[tuple[Optional[str], float]]:
    """
    Gera áudio para múltiplos segmentos em paralelo.

    segments: lista de dicts com keys:
        - text: str
        - voice_id: str
        - emotion: str (default "neutral")
        - context_text: str (default "")

    Retorna lista de (audio_path_or_None, duration_seconds).
    """
    dest = dest_dir or settings.audio_path
    items = []

    for seg in segments:
        text = seg["text"]
        voice = seg.get("voice_id") or FALLBACK_VOICE
        emotion = seg.get("emotion", "neutral")
        ctx = seg.get("context_text", "")

        heuristic = detect_emotion_from_text(text, ctx)
        final_emotion = heuristic if (emotion == "neutral" and heuristic != "neutral") else emotion
        params = EMOTION_SETTINGS.get(final_emotion, EMOTION_SETTINGS["neutral"])

        clean = _prepare_text(text)
        if not clean:
            clean = text.strip()
        if len(clean) > 2000:
            clean = clean[:2000]

        output_path = str(dest / f"{uuid.uuid4().hex}.mp3")
        items.append({
            "text": clean,
            "voice": voice,
            "rate": params["rate"],
            "pitch": params["pitch"],
            "volume": params["volume"],
            "output_path": output_path,
            "emotion": final_emotion,
            "original_text": text,
        })

    # Executa tudo em paralelo numa thread dedicada
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        # Timeout total: TTS_TIMEOUT * número de batches + margem
        total_timeout = TTS_TIMEOUT * len(items) / TTS_CONCURRENCY + 60
        future = pool.submit(asyncio.run, _generate_batch_async(items))
        try:
            paths = future.result(timeout=total_timeout)
        except concurrent.futures.TimeoutError:
            logger.error(f"Batch TTS timeout total após {total_timeout:.0f}s")
            paths = [None] * len(items)

    results = []
    for it, path in zip(items, paths):
        duration = _estimate_duration(it["original_text"], it["rate"])
        results.append((path, duration))
    return results


def generate_audio(
    text: str,
    voice_id: str,
    emotion: str = "neutral",
    context_text: str = "",
    output_dir: Optional[Path] = None,
) -> tuple[str, float]:
    """
    Gera áudio para um único segmento (compatibilidade com código existente).
    Para processamento em lote use generate_audio_batch().
    """
    results = generate_audio_batch(
        [{"text": text, "voice_id": voice_id, "emotion": emotion, "context_text": context_text}],
        dest_dir=output_dir,
    )
    path, duration = results[0]
    if path is None:
        raise RuntimeError(f"TTS falhou para voz {voice_id}")
    return path, duration


# ── Utilitários ───────────────────────────────────────────────────────────────
def _estimate_duration(text: str, rate_str: str = "+0%") -> float:
    words = len(text.split())
    speed = 1.0
    m = re.match(r'([+-])(\d+)%', rate_str)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        pct = float(m.group(2)) / 100
        speed = 1.0 + sign * pct
    return round((words / 150) * 60 / max(speed, 0.3), 2)


def estimate_duration(text: str, speed: float = 1.0) -> float:
    words = len(text.split())
    return round((words / 150) * 60 / max(speed, 0.3), 2)


async def list_available_voices_async() -> list[dict]:
    voices = await edge_tts.list_voices()
    return [{"id": v["ShortName"], "name": v["FriendlyName"], "locale": v["Locale"]} for v in voices]


def list_available_voices() -> list[dict]:
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, list_available_voices_async()).result(timeout=15)
    except Exception:
        return []
