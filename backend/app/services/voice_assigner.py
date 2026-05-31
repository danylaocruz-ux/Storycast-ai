"""
Sistema de Atribuição de Vozes.
Mapeia personagens para vozes do edge-tts (Microsoft, gratuito).
Suporte: PT-BR, EN-US, ES-ES/MX, FR-FR
"""
import logging

logger = logging.getLogger(__name__)

CURATED_VOICES = [
    # ── PT-BR ──────────────────────────────────────────────────────────────
    {"id": "pt-BR-FranciscaNeural",  "name": "Francisca",   "locale": "pt-BR", "gender": "female"},
    {"id": "pt-BR-AntonioNeural",    "name": "Antonio",     "locale": "pt-BR", "gender": "male"},
    {"id": "pt-BR-ThalitaNeural",    "name": "Thalita",     "locale": "pt-BR", "gender": "female"},
    {"id": "pt-BR-DonatoNeural",     "name": "Donato",      "locale": "pt-BR", "gender": "male"},
    {"id": "pt-BR-ElzaNeural",       "name": "Elza",        "locale": "pt-BR", "gender": "female"},
    {"id": "pt-BR-FabioNeural",      "name": "Fabio",       "locale": "pt-BR", "gender": "male"},
    {"id": "pt-BR-GiovannaNeural",   "name": "Giovanna",    "locale": "pt-BR", "gender": "female"},
    {"id": "pt-BR-HumbertoNeural",   "name": "Humberto",    "locale": "pt-BR", "gender": "male"},
    {"id": "pt-BR-JulioNeural",      "name": "Julio",       "locale": "pt-BR", "gender": "male"},
    {"id": "pt-BR-LeilaNeural",      "name": "Leila",       "locale": "pt-BR", "gender": "female"},
    {"id": "pt-BR-NicolauNeural",    "name": "Nicolau",     "locale": "pt-BR", "gender": "male"},
    {"id": "pt-BR-ValeriaNeural",    "name": "Valeria",     "locale": "pt-BR", "gender": "female"},
    {"id": "pt-BR-YaraNeural",       "name": "Yara",        "locale": "pt-BR", "gender": "female"},
    # ── EN-US ──────────────────────────────────────────────────────────────
    {"id": "en-US-DavisNeural",       "name": "Davis",       "locale": "en-US", "gender": "male"},
    {"id": "en-US-JennyNeural",       "name": "Jenny",       "locale": "en-US", "gender": "female"},
    {"id": "en-US-AriaNeural",        "name": "Aria",        "locale": "en-US", "gender": "female"},
    {"id": "en-US-EricNeural",        "name": "Eric",        "locale": "en-US", "gender": "male"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher", "locale": "en-US", "gender": "male"},
    {"id": "en-US-AnaNeural",         "name": "Ana",         "locale": "en-US", "gender": "female"},
    {"id": "en-US-MonicaNeural",      "name": "Monica",      "locale": "en-US", "gender": "female"},
    {"id": "en-US-GuyNeural",         "name": "Guy",         "locale": "en-US", "gender": "male"},
    {"id": "en-US-SaraNeural",        "name": "Sara",        "locale": "en-US", "gender": "female"},
    # ── ES-ES / ES-MX ──────────────────────────────────────────────────────
    {"id": "es-ES-ElviraNeural",      "name": "Elvira",      "locale": "es-ES", "gender": "female"},
    {"id": "es-ES-AlvaroNeural",      "name": "Alvaro",      "locale": "es-ES", "gender": "male"},
    {"id": "es-MX-DaliaNeural",       "name": "Dalia",       "locale": "es-MX", "gender": "female"},
    {"id": "es-MX-JorgeNeural",       "name": "Jorge",       "locale": "es-MX", "gender": "male"},
    {"id": "es-ES-AbrilNeural",       "name": "Abril",       "locale": "es-ES", "gender": "female"},
    {"id": "es-ES-ArnauNeural",       "name": "Arnau",       "locale": "es-ES", "gender": "male"},
    # ── FR-FR ──────────────────────────────────────────────────────────────
    {"id": "fr-FR-DeniseNeural",      "name": "Denise",      "locale": "fr-FR", "gender": "female"},
    {"id": "fr-FR-HenriNeural",       "name": "Henri",       "locale": "fr-FR", "gender": "male"},
    {"id": "fr-FR-EloiseNeural",      "name": "Eloise",      "locale": "fr-FR", "gender": "female"},
]

_VOICE_INDEX = {v["id"]: v for v in CURATED_VOICES}

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


def assign_voice(name, gender, age_group, personality, is_narrator, used_voice_ids):
    candidates = _get_candidates(gender, age_group, personality, is_narrator)
    for voice in candidates:
        if voice["id"] not in used_voice_ids:
            return voice
    for voice in CURATED_VOICES:
        if voice["locale"] == "pt-BR" and voice["id"] not in used_voice_ids:
            return voice
    return candidates[0] if candidates else FALLBACK_VOICE


def _get_candidates(gender, age_group, personality, is_narrator):
    if is_narrator:
        return [DEFAULT_VOICES["narrator_neutral"], DEFAULT_VOICES["female_adult"], DEFAULT_VOICES["male_adult"]]
    if personality == "villain":
        return [DEFAULT_VOICES["villain"], DEFAULT_VOICES["male_adult"] if gender != "female" else DEFAULT_VOICES["female_adult"]]
    if age_group == "child":
        return [DEFAULT_VOICES["child"], DEFAULT_VOICES["female_teen"]]
    if age_group == "elderly":
        return [DEFAULT_VOICES["male_elderly"] if gender != "female" else DEFAULT_VOICES["female_elderly"], DEFAULT_VOICES["male_adult"]]
    if age_group == "teen":
        return [DEFAULT_VOICES["male_teen"] if gender != "female" else DEFAULT_VOICES["female_teen"], DEFAULT_VOICES["male_adult"]]
    if gender == "female":
        return [DEFAULT_VOICES["female_adult"], DEFAULT_VOICES["narrator_neutral"]]
    if gender == "male":
        return [DEFAULT_VOICES["male_adult"], DEFAULT_VOICES["villain"]]
    return [DEFAULT_VOICES["narrator_neutral"], DEFAULT_VOICES["male_adult"]]


def list_available_voices():
    return CURATED_VOICES
