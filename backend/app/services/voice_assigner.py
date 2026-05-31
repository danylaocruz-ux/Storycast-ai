"""
Sistema de Atribuição de Vozes.
Mapeia personagens para vozes do edge-tts (Microsoft, gratuito).
"""
import logging

logger = logging.getLogger(__name__)

# ── Vozes curadas para audiobooks ─────────────────────────────────────────────
# Lista estática para resposta rápida (sem chamar a API do edge-tts)
CURATED_VOICES = [
    # PT-BR
    {"id": "pt-BR-FranciscaNeural",  "name": "Francisca",  "locale": "pt-BR", "gender": "female"},
    {"id": "pt-BR-AntonioNeural",    "name": "Antonio",    "locale": "pt-BR", "gender": "male"},
    {"id": "pt-BR-ThalitaNeural",    "name": "Thalita",    "locale": "pt-BR", "gender": "female"},
    {"id": "pt-BR-DonatoNeural",     "name": "Donato",     "locale": "pt-BR", "gender": "male"},
    {"id": "pt-BR-ElzaNeural",       "name": "Elza",       "locale": "pt-BR", "gender": "female"},
    {"id": "pt-BR-FabioNeural",      "name": "Fabio",      "locale": "pt-BR", "gender": "male"},
    {"id": "pt-BR-GiovannaNeural",   "name": "Giovanna",   "locale": "pt-BR", "gender": "female"},
    {"id": "pt-BR-HumbertoNeural",   "name": "Humberto",   "locale": "pt-BR", "gender": "male"},
    {"id": "pt-BR-JulioNeural",      "name": "Julio",      "locale": "pt-BR", "gender": "male"},
    {"id": "pt-BR-LeilaNeural",      "name": "Leila",      "locale": "pt-BR", "gender": "female"},
    {"id": "pt-BR-NicolauNeural",    "name": "Nicolau",    "locale": "pt-BR", "gender": "male"},
    {"id": "pt-BR-ValeriaNeural",    "name": "Valeria",    "locale": "pt-BR", "gender": "female"},
    {"id": "pt-BR-YaraNeural",       "name": "Yara",       "locale": "pt-BR", "gender": "female"},
    # EN-US
    {"id": "en-US-DavisNeural",      "name": "Davis",      "locale": "en-US", "gender": "male"},
    {"id": "en-US-JennyNeural",      "name": "Jenny",      "locale": "en-US", "gender": "female"},
    {"id": "en-US-AriaNeural",       "name": "Aria",       "locale": "en-US", "gender": "female"},
    {"id": "en-US-EricNeural",       "name": "Eric",       "locale": "en-US", "gender": "male"},
    {"id": "en-US-ChristopherNeural","name": "Christopher","locale": "en-US", "gender": "male"},
    {"id": "en-US-AnaNeural",        "name": "Ana",        "locale": "en-US", "gender": "female"},
    {"id": "en-US-MonicaNeural",     "name": "Monica",     "locale": "en-US", "gender": "female"},
]

# Índice rápido id → voice
_VOICE_INDEX = {v["id"]: v for v in CURATED_VOICES}

# Mapeamento perfil → voz padrão (fallback)
DEFAULT_VOICES = {
    "narrator_neutral": {"id": "pt-BR-FranciscaNeural",   "name": "Francisca"},
    "male_adult":       {"id": "pt-BR-AntonioNeural",      "name": "Antonio"},
    "male_elderly":     {"id": "en-US-ChristopherNeural",  "name": "Christopher"},
    "male_teen":        {"id": "en-US-EricNeural",         "name": "Eric"},
    "female_adult":     {"id": "pt-BR-ThalitaNeural",      "name": "Thalita"},
    "female_elderly":   {"id": "en-US-MonicaNeural",       "name": "Monica"},
    "female_teen":      {"id": "en-US-AriaNeural",         "name": "Aria"},
    "child":            {"id": "en-US-AnaNeural",          "name": "Ana"},
    "villain":          {"id": "en-US-DavisNeural",        "name": "Davis"},
}

FALLBACK_VOICE = {"id": "pt-BR-FranciscaNeural", "name": "Francisca"}


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

    # Todas as candidatas já usadas → pega qualquer PT-BR não usada
    for voice in CURATED_VOICES:
        if voice["locale"] == "pt-BR" and voice["id"] not in used_voice_ids:
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


def list_available_voices() -> list[dict]:
    """Retorna a lista curada de vozes disponíveis para audiobook."""
    return CURATED_VOICES
