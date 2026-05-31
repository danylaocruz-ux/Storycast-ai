"""
Sistema de Atribuição de Vozes.
Mapeia personagens para vozes do edge-tts (Microsoft, gratuito).
"""
import logging
from ..services.tts_service import list_available_voices

logger = logging.getLogger(__name__)

# Vozes edge-tts por perfil (ShortName do Microsoft TTS)
DEFAULT_VOICES = {
    "narrator_neutral": {"id": "pt-BR-FranciscaNeural",   "name": "Francisca (PT-BR)"},
    "male_adult":       {"id": "pt-BR-AntonioNeural",      "name": "Antonio (PT-BR)"},
    "male_elderly":     {"id": "en-US-ChristopherNeural",  "name": "Christopher"},
    "male_teen":        {"id": "en-US-EricNeural",         "name": "Eric"},
    "female_adult":     {"id": "en-US-JennyNeural",        "name": "Jenny"},
    "female_elderly":   {"id": "en-US-MonicaNeural",       "name": "Monica"},
    "female_teen":      {"id": "en-US-AriaNeural",         "name": "Aria"},
    "child":            {"id": "en-US-AnaNeural",          "name": "Ana"},
    "villain":          {"id": "en-US-DavisNeural",        "name": "Davis"},
}

FALLBACK_VOICE = {"id": "pt-BR-FranciscaNeural", "name": "Francisca (PT-BR)"}


def assign_voice(
    name: str,
    gender: str,
    age_group: str,
    personality: str,
    is_narrator: bool,
    used_voice_ids: set[str],
) -> dict:
    """
    Atribui a melhor voz disponível ao personagem.
    Evita repetir vozes já usadas em outros personagens.
    """
    candidates = _get_candidates(gender, age_group, personality, is_narrator)

    for voice in candidates:
        if voice["id"] not in used_voice_ids:
            return voice

    # Todas as candidatas já usadas → pega qualquer não usada
    for voice in DEFAULT_VOICES.values():
        if voice["id"] not in used_voice_ids:
            return voice

    # Último recurso
    return candidates[0] if candidates else FALLBACK_VOICE


def _get_candidates(
    gender: str, age_group: str, personality: str, is_narrator: bool
) -> list[dict]:
    if is_narrator:
        return [
            DEFAULT_VOICES["narrator_neutral"],
            DEFAULT_VOICES["female_adult"],
            DEFAULT_VOICES["male_adult"],
        ]

    if personality == "villain":
        return [
            DEFAULT_VOICES["villain"],
            DEFAULT_VOICES["male_adult"] if gender != "female" else DEFAULT_VOICES["female_adult"],
        ]

    if age_group == "child":
        return [DEFAULT_VOICES["child"], DEFAULT_VOICES["female_teen"]]

    if age_group == "elderly":
        return [
            DEFAULT_VOICES["male_elderly"] if gender != "female" else DEFAULT_VOICES["female_elderly"],
            DEFAULT_VOICES["male_adult"],
            DEFAULT_VOICES["female_adult"],
        ]

    if age_group == "teen":
        return [
            DEFAULT_VOICES["male_teen"] if gender != "female" else DEFAULT_VOICES["female_teen"],
            DEFAULT_VOICES["male_adult"],
        ]

    # Adulto padrão
    if gender == "female":
        return [DEFAULT_VOICES["female_adult"], DEFAULT_VOICES["narrator_neutral"]]
    if gender == "male":
        return [DEFAULT_VOICES["male_adult"], DEFAULT_VOICES["villain"]]

    return [DEFAULT_VOICES["narrator_neutral"], DEFAULT_VOICES["male_adult"]]


def list_available_voices_api() -> list[dict]:
    """Lista vozes disponíveis no edge-tts."""
    try:
        return list_available_voices()
    except Exception as e:
        logger.error(f"Erro ao listar vozes: {e}")
        return list(DEFAULT_VOICES.values())
