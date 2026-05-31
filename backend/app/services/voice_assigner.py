"""
Sistema de Atribuição de Vozes.
Mapeia personagens para voice_ids do ElevenLabs.
Garante persistência e não repetição de vozes.
"""
import logging
from elevenlabs import ElevenLabs
from ..config import settings

logger = logging.getLogger(__name__)

# ── Vozes padrão por perfil (voice_id do ElevenLabs) ─────────────────────────
# Estes são IDs públicos/pré-construídos do ElevenLabs.
# Atualize com os IDs reais da sua conta se necessário.
DEFAULT_VOICES = {
    "narrator_neutral": {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah"},      # Voz calma e clara
    "male_adult":       {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh"},        # Adulto masculino
    "male_elderly":     {"id": "VR6AewLTigWG4xSOukaG", "name": "Arnold"},      # Voz madura masculina
    "male_teen":        {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam"},        # Tom mais jovem
    "female_adult":     {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel"},      # Adulta feminina
    "female_elderly":   {"id": "D38z5RcWu1voky8WS1ja", "name": "Dorothy"},     # Voz madura feminina
    "female_teen":      {"id": "ThT5KcBeYPX3keUQqHPh", "name": "Nicole"},      # Adolescente feminina
    "child":            {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi"},        # Voz infantil
    "villain":          {"id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam"},         # Voz mais intensa
}

# Fallback quando acabar vozes distintas
FALLBACK_VOICE = {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah"}


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
    all_voices = list(DEFAULT_VOICES.values())
    for voice in all_voices:
        if voice["id"] not in used_voice_ids:
            return voice

    # Último recurso: repete a voz mais adequada
    return candidates[0] if candidates else FALLBACK_VOICE


def _get_candidates(
    gender: str, age_group: str, personality: str, is_narrator: bool
) -> list[dict]:
    """Retorna lista de vozes candidatas ordenadas por prioridade."""
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
        return [DEFAULT_VOICES["child"]]

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

    # Neutro
    return [DEFAULT_VOICES["narrator_neutral"], DEFAULT_VOICES["male_adult"]]


def list_available_voices() -> list[dict]:
    """Lista vozes disponíveis na conta ElevenLabs."""
    if not settings.ELEVENLABS_API_KEY:
        return list(DEFAULT_VOICES.values())
    try:
        el = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
        voices_resp = el.voices.get_all()
        return [
            {"id": v.voice_id, "name": v.name, "labels": v.labels or {}}
            for v in voices_resp.voices
        ]
    except Exception as e:
        logger.error(f"Erro ao listar vozes ElevenLabs: {e}")
        return list(DEFAULT_VOICES.values())
