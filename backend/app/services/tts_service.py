"""
Serviço de Text-to-Speech com expressão emocional.
Usa edge-tts (Microsoft) com ajustes de prosódia por emoção.
"""
import asyncio
import concurrent.futures
import re
import uuid
import logging
from pathlib import Path
import edge_tts
from ..config import settings

logger = logging.getLogger(__name__)

TTS_TIMEOUT = 45

# ── Configurações emocionais expressivas ──────────────────────────────────────
# Valores calibrados para soar dramático mas natural (como rádio-novela)
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

# Verbos de fala que indicam emoção específica
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

# Pontuação que indica emoção
_PUNCT_EMOTION: list[tuple[str, str]] = [
    (r"!{2,}", "angry"),          # !!! = raiva/grito
    (r"\?{2,}", "surprised"),     # ??? = surpresa
    (r"\.{3,}", "suspenseful"),   # ... = suspense/hesitação
    (r"!\?", "surprised"),        # !? = surpresa/indignação
]


def detect_emotion_from_text(text: str, context_text: str = "") -> str:
    """
    Detecta emoção por heurística: verbos de fala e pontuação.
    Combina o texto do bloco com o texto de contexto (linha seguinte com atribuição).
    """
    combined = (text + " " + context_text).lower()

    # Checa verbos de emoção no contexto
    for emotion, verbs in _EMOTION_VERBS.items():
        for verb in verbs:
            if verb in combined:
                return emotion

    # Checa pontuação do texto original
    for pattern, emotion in _PUNCT_EMOTION:
        if re.search(pattern, text):
            return emotion

    return "neutral"


# ── Preparação de texto ───────────────────────────────────────────────────────

def _prepare_text(text: str) -> str:
    """Limpa texto para TTS sem perder a expressividade."""
    # Remove travessão inicial (causa pausa artificial)
    text = re.sub(r'^[—–]\s*', '', text.strip())

    # Normaliza múltiplas quebras e espaços
    text = re.sub(r'\n{2,}', ' ', text)
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r' {2,}', ' ', text)

    # Mantém reticências (indicam pausa dramática) mas normaliza excesso
    text = re.sub(r'\.{4,}', '...', text)

    # Remove travessão de atribuição no final: "texto — disse X" → "texto"
    # O nome do personagem já foi usado para selecionar a voz
    text = re.sub(r'\s*[—–]\s*(disse|falou|respondeu|perguntou|exclamou|murmurou|gritou|sussurrou)\s+\w+.*$',
                  '', text, flags=re.IGNORECASE)

    return text.strip()


# ── Geração de áudio ──────────────────────────────────────────────────────────

async def _generate_async(
    text: str, voice: str, rate: str, pitch: str, volume: str, output_path: str
) -> None:
    """Gera áudio com os parâmetros de emoção aplicados."""
    communicate = edge_tts.Communicate(
        text, voice,
        rate=rate,
        pitch=pitch,
        volume=volume,
    )
    await asyncio.wait_for(communicate.save(output_path), timeout=TTS_TIMEOUT)


def _run_tts(coro, timeout: float = TTS_TIMEOUT + 5) -> None:
    """Executa coroutine TTS em thread dedicada com timeout."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        future.result(timeout=timeout)


def generate_audio(
    text: str,
    voice_id: str,
    emotion: str = "neutral",
    context_text: str = "",
    output_dir: Path | None = None,
) -> tuple[str, float]:
    """
    Gera áudio com expressão emocional.
    
    - emotion: emoção base vinda do LLM
    - context_text: texto de contexto para refinar detecção de emoção
    - Aplica heurística local para refinar a emoção se necessário
    """
    # Refina emoção com heurística local (pontuação + verbos)
    heuristic_emotion = detect_emotion_from_text(text, context_text)
    # Heurística sobrepõe "neutral" mas não sobrepõe emoções fortes do LLM
    final_emotion = heuristic_emotion if (emotion == "neutral" and heuristic_emotion != "neutral") else emotion

    params = EMOTION_SETTINGS.get(final_emotion, EMOTION_SETTINGS["neutral"])
    dest_dir = output_dir or settings.audio_path
    filename = f"{uuid.uuid4().hex}.mp3"
    dest = str(dest_dir / filename)

    clean = _prepare_text(text)
    if not clean:
        clean = text.strip()
    if len(clean) > 2000:
        clean = clean[:2000]

    logger.debug(f"TTS voice={voice_id} emotion={final_emotion} rate={params['rate']} pitch={params['pitch']}: {clean[:60]}")

    try:
        _run_tts(_generate_async(
            text=clean,
            voice=voice_id or FALLBACK_VOICE,
            rate=params["rate"],
            pitch=params["pitch"],
            volume=params["volume"],
            output_path=dest,
        ))
        words = len(text.split())
        speed_factor = 1.0
        if "+" in params["rate"]:
            pct = float(params["rate"].replace("+", "").replace("%", "")) / 100
            speed_factor = 1 + pct
        elif "-" in params["rate"]:
            pct = float(params["rate"].replace("-", "").replace("%", "")) / 100
            speed_factor = 1 - pct
        duration = (words / 150) * 60 / max(speed_factor, 0.3)
        return dest, round(duration, 2)

    except (concurrent.futures.TimeoutError, asyncio.TimeoutError, TimeoutError):
        logger.warning(f"TTS timeout ({TTS_TIMEOUT}s) voice={voice_id}. Fallback neutro...")
        Path(dest).unlink(missing_ok=True)
        return _try_fallback(clean, dest_dir)

    except Exception as e:
        logger.warning(f"Erro TTS (voice={voice_id}): {e}. Fallback...")
        Path(dest).unlink(missing_ok=True)
        return _try_fallback(clean, dest_dir)


def _try_fallback(text: str, dest_dir: Path) -> tuple[str, float]:
    """Fallback para voz padrão com emoção neutra."""
    filename = f"{uuid.uuid4().hex}.mp3"
    dest = str(dest_dir / filename)
    try:
        _run_tts(
            _generate_async(
                text=text[:800],
                voice=FALLBACK_VOICE,
                rate="+0%",
                pitch="+0Hz",
                volume="+0%",
                output_path=dest,
            ),
            timeout=30,
        )
        words = len(text[:800].split())
        return dest, round((words / 150) * 60, 2)
    except Exception as e2:
        logger.error(f"Fallback TTS também falhou: {e2}")
        raise


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
