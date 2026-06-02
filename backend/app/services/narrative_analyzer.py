"""
Motor de Análise Narrativa — lógica de rádio-novela com detecção de emoções.
"""
import re
import json
import logging
from ..config import settings

logger = logging.getLogger(__name__)
_client = None


def _get_client():
    global _client
    if _client is None:
        from groq import Groq
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY não configurada")
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


_DIALOGUE_STARTERS = ('—', '–', '"', '"', '"')

_SPEECH_VERBS = (
    r"(?:disse|falou|respondeu|perguntou|exclamou|murmurou|gritou|sussurrou|"
    r"completou|continuou|acrescentou|interrompeu|replicou|ordenou|pediu|"
    r"chamou|berrou|cochichou|afirmou|negou|concordou|discordou|admitiu|"
    r"confessou|explicou|anunciou|declarou|suplicou|implorou|resmungou|"
    r"chorou|soluçou|riu|gargalhou|tremeu|gaguejou|vociferou|rosnou)"
)
_NAME_PATTERN = r"([A-ZÁÉÍÓÚÂÊÔÃÕÜ][a-záéíóúâêôãõü]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÜ][a-záéíóúâêôãõü]+)?)"

# Mapeamento verbo → emoção
_VERB_EMOTION: dict[str, str] = {
    "gritou": "angry", "berrou": "shouting", "rosnou": "angry",
    "vociferou": "angry", "protestou": "angry",
    "chorou": "crying", "soluçou": "crying",
    "murmurou": "whispering", "sussurrou": "whispering", "cochichou": "whispering",
    "exclamou": "surprised", "riu": "happy", "gargalhou": "happy",
    "tremeu": "fearful", "gaguejou": "fearful",
    "suplicou": "sad", "implorou": "sad", "lamentou": "sad",
    "pausou": "suspenseful", "hesitou": "suspenseful",
}


def _is_dialogue(text: str) -> bool:
    return text.lstrip().startswith(_DIALOGUE_STARTERS)


def _find_speaker_in_text(text: str, character_names: list[str]) -> str | None:
    for m in re.findall(_SPEECH_VERBS + r"\s+" + _NAME_PATTERN, text, re.IGNORECASE):
        candidate = m[-1] if isinstance(m, tuple) else m
        for name in character_names:
            if candidate.lower() in (name.lower(), name.split()[0].lower()):
                return name
    for m in re.findall(_NAME_PATTERN + r"\s+" + _SPEECH_VERBS, text, re.IGNORECASE):
        candidate = m[0] if isinstance(m, tuple) else m
        for name in character_names:
            if candidate.lower() in (name.lower(), name.split()[0].lower()):
                return name
    return None


def _detect_emotion_from_verb(text: str) -> str | None:
    """Detecta emoção a partir do verbo de fala presente no texto."""
    for verb, emotion in _VERB_EMOTION.items():
        if re.search(r'\b' + verb + r'\b', text, re.IGNORECASE):
            return emotion
    # Pontuação
    if re.search(r'!{2,}', text): return "angry"
    if re.search(r'\?{2,}', text): return "surprised"
    if re.search(r'\.{3,}', text): return "suspenseful"
    return None


def _heuristic_with_context(
    text: str, prev_text: str | None, next_text: str | None,
    character_names: list[str],
) -> dict | None:
    if not _is_dialogue(text):
        return None

    # Emoção do verbo inline
    emotion = _detect_emotion_from_verb(text) or "neutral"

    # Atribuição inline: — Texto — disse Pedro.
    speaker = _find_speaker_in_text(text, character_names)
    if speaker:
        # Refina emoção com verbo da atribuição
        emotion_from_attr = _detect_emotion_from_verb(text) or emotion
        return {"character_name": speaker, "emotion": emotion_from_attr}

    # Atribuição na linha seguinte
    if next_text and not _is_dialogue(next_text):
        speaker = _find_speaker_in_text(next_text, character_names)
        if speaker:
            emotion = _detect_emotion_from_verb(next_text) or emotion
            return {"character_name": speaker, "emotion": emotion}

    # Atribuição na linha anterior
    if prev_text and not _is_dialogue(prev_text):
        speaker = _find_speaker_in_text(prev_text, character_names)
        if speaker:
            emotion = _detect_emotion_from_verb(prev_text) or emotion
            return {"character_name": speaker, "emotion": emotion}

    return None


# ── Extração de personagens ───────────────────────────────────────────────────

def _prescan_dialogue_names(text: str) -> list[str]:
    found: set[str] = set()
    for m in re.findall(_SPEECH_VERBS + r"\s+" + _NAME_PATTERN, text, re.IGNORECASE):
        name = m[-1] if isinstance(m, tuple) else m
        if len(name) >= 3:
            found.add(name)
    for m in re.findall(_NAME_PATTERN + r"\s+" + _SPEECH_VERBS, text, re.IGNORECASE):
        name = m[0] if isinstance(m, tuple) else m
        if len(name) >= 3:
            found.add(name)
    return sorted(found)


def _multi_section_sample(text: str, section_size: int = 3500) -> list[str]:
    sections, n = [], len(text)
    sections.append(text[:section_size])
    if n > section_size * 2:
        mid = n // 2
        sections.append(text[max(0, mid - section_size // 2):mid + section_size // 2])
    if n > section_size * 3:
        sections.append(text[max(0, n - section_size):])
    return sections


CHARACTER_EXTRACTION_PROMPT = """Você é um analista literário. Analise o texto e identifique TODOS os personagens.

{hint}

Retorne APENAS este JSON (sem markdown):
{{
  "characters": [
    {{
      "name": "Nome",
      "description": "1-2 frases",
      "gender": "male | female | neutral",
      "age_group": "child | teen | adult | elderly",
      "personality": "hero | villain | narrator | secondary | other",
      "is_narrator": false,
      "appearance_order": 1
    }}
  ]
}}

REGRAS:
1. SEMPRE inclua "Narrador" como primeiro item (is_narrator: true)
2. Identifique quem FALA — procure travessões (—) e verbos: disse, falou, respondeu, gritou, murmurou...
3. Não duplique personagens
4. Máximo 20 personagens

TEXTO:
{text}
"""


def extract_characters(text: str) -> list[dict]:
    regex_names = _prescan_dialogue_names(text)
    logger.info(f"Pré-scan: {len(regex_names)} nomes — {regex_names[:10]}")
    sections = _multi_section_sample(text, 3000)
    combined = "\n\n[...]\n\n".join(sections)
    hint = f"Nomes encontrados em diálogos: {', '.join(regex_names[:20])}" if regex_names else ""

    try:
        resp = _get_client().chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": CHARACTER_EXTRACTION_PROMPT.format(
                text=combined, hint=hint)}],
            temperature=0.1,
            max_tokens=2500,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        characters = data.get("characters", [])
        logger.info(f"Personagens: {[c.get('name') for c in characters]}")

        if not any(c.get("is_narrator") for c in characters):
            characters.insert(0, _default_narrator())

        if not [c for c in characters if not c.get("is_narrator")] and regex_names:
            characters = [_default_narrator()]
            for i, name in enumerate(regex_names[:10], 1):
                characters.append({"name": name, "description": "Personagem do livro",
                    "gender": "neutral", "age_group": "adult", "personality": "secondary",
                    "is_narrator": False, "appearance_order": i})

        for i, c in enumerate(characters):
            c["appearance_order"] = i
        return characters

    except Exception as e:
        logger.error(f"Erro extract_characters: {e}")
        if regex_names:
            chars = [_default_narrator()]
            for i, name in enumerate(regex_names[:10], 1):
                chars.append({"name": name, "description": "Personagem", "gender": "neutral",
                    "age_group": "adult", "personality": "secondary", "is_narrator": False,
                    "appearance_order": i})
            return chars
        return [_default_narrator()]


# ── Análise de segmentos ──────────────────────────────────────────────────────

def analyze_segments_batch(
    segments: list[str],
    character_names: list[str],
    batch_size: int = 8,
) -> list[dict]:
    results: list[dict | None] = [None] * len(segments)

    # Heurística com contexto
    for i, seg in enumerate(segments):
        prev = segments[i - 1] if i > 0 else None
        nxt = segments[i + 1] if i < len(segments) - 1 else None
        r = _heuristic_with_context(seg, prev, nxt, character_names)
        if r:
            results[i] = r

    unknown = [i for i, r in enumerate(results) if r is None]
    logger.info(f"Heurística: {len(segments) - len(unknown)}/{len(segments)} resolvidos")

    if not unknown:
        return results  # type: ignore

    # LLM para os não resolvidos — com contexto E instrução de emoção
    BATCH_PROMPT = """Analise os blocos de texto de um livro/novela para rádio-novela.
Para cada bloco [N], identifique: (1) quem fala e (2) qual a emoção.

Personagens disponíveis: {character_names}

REGRAS:
1. Blocos com — ou aspas = FALA de personagem (nunca "Narrador")
2. A atribuição ("disse X", "gritou X") pode estar no CONTEXTO_ANTES ou CONTEXTO_DEPOIS
3. Descrição/ação/narração = "Narrador"
4. character_name DEVE ser exatamente um dos personagens disponíveis
5. Retorne exatamente {count} resultados

EMOÇÕES — escolha com base no contexto emocional:
- neutral: conversa normal, narração simples
- happy: alegre, animado, comemorando ("riu", "sorriu", "animado")
- sad: triste, deprimido, sofrendo ("chorou", "soluçou", "tristeza")
- angry: irritado, com raiva, gritando ("gritou", "berrou", "raiva", "!!!")
- fearful: com medo, assustado, nervoso ("tremeu", "medo", "apavorado")
- surprised: surpreso, chocado, incrédulo ("exclamou", "!?", "incrédulo")
- romantic: apaixonado, carinhoso, sussurrando de amor
- suspenseful: tensão, mistério, hesitação ("...", "pausou", "silêncio")
- whispering: sussurrando, falando baixo ("murmurou", "sussurrou")
- crying: chorando enquanto fala ("entre lágrimas", "chorando")
- shouting: gritando alto ("berrou com toda força", "!!!")

{blocks}

JSON: {{"results": [{{"character_name": "nome", "emotion": "emoção"}}, ...]}}"""

    for batch_start in range(0, len(unknown), batch_size):
        batch_idx = unknown[batch_start:batch_start + batch_size]
        block_lines = []
        for rank, idx in enumerate(batch_idx, 1):
            prev_ctx = segments[idx - 1][:120] if idx > 0 else "(início)"
            next_ctx = segments[idx + 1][:120] if idx < len(segments) - 1 else "(fim)"
            seg_text = segments[idx][:600]
            block_lines.append(
                f"[{rank}] CONTEXTO_ANTES: {prev_ctx}\n"
                f"[{rank}] BLOCO: {seg_text}\n"
                f"[{rank}] CONTEXTO_DEPOIS: {next_ctx}"
            )

        try:
            resp = _get_client().chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": BATCH_PROMPT.format(
                    character_names=", ".join(character_names),
                    count=len(batch_idx),
                    blocks="\n\n".join(block_lines),
                )}],
                temperature=0.2,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            llm_res = data.get("results", [])

            for rank, idx in enumerate(batch_idx):
                if rank < len(llm_res):
                    r = llm_res[rank]
                    char = r.get("character_name", "Narrador")
                    if char not in character_names:
                        char = next(
                            (n for n in character_names if n.split()[0].lower() == char.lower()),
                            "Narrador",
                        )
                    emotion = r.get("emotion", "neutral")
                    # Valida emoção
                    valid_emotions = {"neutral", "happy", "excited", "sad", "angry", "fearful",
                                      "surprised", "romantic", "suspenseful", "whispering",
                                      "crying", "shouting"}
                    if emotion not in valid_emotions:
                        emotion = "neutral"
                    results[idx] = {"character_name": char, "emotion": emotion}
                else:
                    results[idx] = {"character_name": "Narrador", "emotion": "neutral"}

        except Exception as e:
            logger.warning(f"Erro LLM batch {batch_start}: {e}")
            for idx in batch_idx:
                if results[idx] is None:
                    fallback_char = "Narrador" if not _is_dialogue(segments[idx]) else (
                        character_names[1] if len(character_names) > 1 else "Narrador"
                    )
                    results[idx] = {"character_name": fallback_char, "emotion": "neutral"}

    for i in range(len(results)):
        if results[i] is None:
            results[i] = {"character_name": "Narrador", "emotion": "neutral"}

    return results  # type: ignore


def _default_narrator() -> dict:
    return {
        "name": "Narrador", "description": "Voz narrativa da história",
        "gender": "neutral", "age_group": "adult",
        "personality": "narrator", "is_narrator": True, "appearance_order": 0,
    }
