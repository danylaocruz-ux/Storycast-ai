"""
Motor de Análise Narrativa — lógica de rádio-novela.
Cada bloco de texto é analisado com contexto dos blocos vizinhos
para identificar corretamente o falante, mesmo quando a atribuição
("disse Pedro", "respondeu Ana") está em outra linha.
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


# ── Constantes ────────────────────────────────────────────────────────────────

_DIALOGUE_STARTERS = ('—', '–', '"', '“', '”')

_SPEECH_VERBS = (
    r"(?:disse|falou|respondeu|perguntou|exclamou|murmurou|gritou|sussurrou|"
    r"completou|continuou|acrescentou|interrompeu|replicou|ordenou|pediu|"
    r"chamou|berrou|cochichou|afirmou|negou|concordou|discordou|admitiu|"
    r"confessou|explicou|anunciou|declarou|suplicou|implorou|resmungou)"
)
_NAME_PATTERN = r"([A-ZÁÉÍÓÚÂÊÔÃÕÜ][a-záéíóúâêôãõü]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÜ][a-záéíóúâêôãõü]+)?)"


def _is_dialogue(text: str) -> bool:
    return text.lstrip().startswith(_DIALOGUE_STARTERS)


def _find_speaker_in_text(text: str, character_names: list[str]) -> str | None:
    """Busca atribuição de fala na própria linha: '— Texto — disse Pedro.'"""
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


def _heuristic_with_context(
    text: str,
    prev_text: str | None,
    next_text: str | None,
    character_names: list[str],
) -> dict | None:
    """
    Heurística com contexto de linhas vizinhas.
    Importante: '— Fala' seguido de 'disse Pedro' em linha separada.
    """
    if not _is_dialogue(text):
        return None  # narração → LLM decide

    # 1. Atribuição na própria linha: — Texto — disse Pedro.
    speaker = _find_speaker_in_text(text, character_names)
    if speaker:
        return {"character_name": speaker, "emotion": "neutral"}

    # 2. Atribuição no próximo bloco (linha seguinte de narração/atribuição)
    if next_text and not _is_dialogue(next_text):
        speaker = _find_speaker_in_text(next_text, character_names)
        if speaker:
            return {"character_name": speaker, "emotion": "neutral"}

    # 3. Atribuição no bloco anterior
    if prev_text and not _is_dialogue(prev_text):
        speaker = _find_speaker_in_text(prev_text, character_names)
        if speaker:
            return {"character_name": speaker, "emotion": "neutral"}

    # É diálogo mas não achamos o falante → LLM com contexto completo
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
1. SEMPRE inclua "Narrador" como primeiro item (is_narrator: true, appearance_order: 0)
2. Identifique personagens que FALAM — procure travessões (—) e verbos: disse, falou, respondeu...
3. Não duplique personagens
4. Máximo 20 personagens

TEXTO:
{text}
"""


def extract_characters(text: str) -> list[dict]:
    regex_names = _prescan_dialogue_names(text)
    logger.info(f"Pré-scan: {len(regex_names)} nomes — {regex_names[:10]}")

    sections = _multi_section_sample(text, section_size=3000)
    combined = "\n\n[...]\n\n".join(sections)

    hint = ""
    if regex_names:
        hint = f"Dica: Os seguintes nomes aparecem em padrões de diálogo: {', '.join(regex_names[:20])}"

    try:
        resp = _get_client().chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": CHARACTER_EXTRACTION_PROMPT.format(
                text=combined, hint=hint
            )}],
            temperature=0.1,
            max_tokens=2500,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        characters = data.get("characters", [])
        logger.info(f"LLM retornou {len(characters)} personagens: {[c.get('name') for c in characters]}")

        has_narrator = any(c.get("is_narrator") for c in characters)
        if not has_narrator:
            characters.insert(0, _default_narrator())

        if len([c for c in characters if not c.get("is_narrator")]) == 0 and regex_names:
            logger.warning("LLM retornou só narrador — usando regex como fallback")
            characters = [_default_narrator()]
            for i, name in enumerate(regex_names[:10], 1):
                characters.append({
                    "name": name, "description": "Personagem do livro",
                    "gender": "neutral", "age_group": "adult",
                    "personality": "secondary", "is_narrator": False,
                    "appearance_order": i,
                })

        for i, c in enumerate(characters):
            c["appearance_order"] = i
        return characters

    except Exception as e:
        logger.error(f"Erro ao extrair personagens: {e}")
        if regex_names:
            chars = [_default_narrator()]
            for i, name in enumerate(regex_names[:10], 1):
                chars.append({"name": name, "description": "Personagem", "gender": "neutral",
                               "age_group": "adult", "personality": "secondary",
                               "is_narrator": False, "appearance_order": i})
            return chars
        return [_default_narrator()]


# ── Análise de segmentos com contexto ────────────────────────────────────────

# Prompt para análise individual com contexto
SEGMENT_WITH_CONTEXT_PROMPT = """Identifique o falante do trecho marcado como [ANALISAR].

Personagens disponíveis: {character_names}

CONTEXTO ANTERIOR: {prev}
[ANALISAR]: {text}
CONTEXTO POSTERIOR: {next}

REGRAS:
- Se [ANALISAR] começa com — ou aspas = FALA de um personagem
- A atribuição ("disse X", "respondeu X") pode estar no CONTEXTO ANTERIOR ou POSTERIOR
- Se for descrição/narração = "Narrador"
- character_name deve ser EXATAMENTE um dos personagens disponíveis

Retorne APENAS JSON: {{"character_name": "nome exato", "emotion": "neutral"}}
Emoções: neutral, happy, sad, angry, fearful, surprised, romantic, suspenseful"""


def analyze_segments_batch(
    segments: list[str],
    character_names: list[str],
    batch_size: int = 8,
) -> list[dict]:
    """
    Analisa segmentos em lote com contexto de vizinhos.
    Cada segmento é analisado com o bloco anterior e posterior visíveis,
    permitindo encontrar atribuições cross-line.
    """
    results: list[dict | None] = [None] * len(segments)

    # Passo 1: heurísticas com contexto vizinho
    for i, seg in enumerate(segments):
        prev = segments[i - 1] if i > 0 else None
        nxt = segments[i + 1] if i < len(segments) - 1 else None
        r = _heuristic_with_context(seg, prev, nxt, character_names)
        if r:
            results[i] = r

    unknown_indices = [i for i, r in enumerate(results) if r is None]
    logger.info(f"Heurística resolveu {len(segments) - len(unknown_indices)}/{len(segments)} segmentos")

    if not unknown_indices:
        return results  # type: ignore

    # Passo 2: LLM em lotes para os não resolvidos, com contexto
    BATCH_PROMPT = """Você está analisando blocos de texto de um livro como uma rádio-novela.
Para cada bloco numerado [N], identifique o falante/narrador.

REGRAS OBRIGATÓRIAS:
1. Bloco que começa com — ou aspas = FALA de personagem (não narrador)
2. A atribuição do falante ("disse X", "respondeu X") pode estar NO MESMO bloco ou nos BLOCOS VIZINHOS mostrados
3. Narração/descrição/ação = "Narrador"
4. character_name DEVE ser exatamente um dos personagens: {character_names}
5. Retorne exatamente {count} resultados na ordem dos blocos numerados

{blocks}

Retorne APENAS JSON:
{{"results": [{{"character_name": "nome", "emotion": "neutral"}}, ...]}}
Emoções: neutral, happy, sad, angry, fearful, surprised, romantic, suspenseful"""

    for batch_start in range(0, len(unknown_indices), batch_size):
        batch_indices = unknown_indices[batch_start:batch_start + batch_size]

        # Monta os blocos com contexto vizinho
        block_lines = []
        for rank, idx in enumerate(batch_indices, 1):
            prev = segments[idx - 1][:100] if idx > 0 else "(início)"
            nxt = segments[idx + 1][:100] if idx < len(segments) - 1 else "(fim)"
            seg_text = segments[idx][:500]
            block_lines.append(
                f"[{rank}] CONTEXTO_ANTES: {prev}\n"
                f"[{rank}] FALA/NARRAÇÃO: {seg_text}\n"
                f"[{rank}] CONTEXTO_DEPOIS: {nxt}"
            )

        blocks_text = "\n\n".join(block_lines)

        try:
            resp = _get_client().chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": BATCH_PROMPT.format(
                    character_names=", ".join(character_names),
                    count=len(batch_indices),
                    blocks=blocks_text,
                )}],
                temperature=0.1,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            llm_results = data.get("results", [])

            for rank, idx in enumerate(batch_indices):
                if rank < len(llm_results):
                    r = llm_results[rank]
                    char = r.get("character_name", "Narrador")
                    if char not in character_names:
                        # Tenta match parcial por primeiro nome
                        matched = next(
                            (n for n in character_names if n.split()[0].lower() == char.lower()),
                            "Narrador"
                        )
                        char = matched
                    results[idx] = {"character_name": char, "emotion": r.get("emotion", "neutral")}
                else:
                    results[idx] = {"character_name": "Narrador", "emotion": "neutral"}

        except Exception as e:
            logger.warning(f"Erro LLM batch {batch_start}: {e}")
            for idx in batch_indices:
                if results[idx] is None:
                    results[idx] = {
                        "character_name": "Narrador" if not _is_dialogue(segments[idx]) else character_names[1] if len(character_names) > 1 else "Narrador",
                        "emotion": "neutral",
                    }

    # Fallback para qualquer None restante
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
