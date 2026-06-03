"""
Motor de Análise Narrativa — rádio-novela com foco em velocidade e resiliência.
Estratégia: heurística máxima + LLM apenas para casos ambíguos (cap de 40 blocos).
"""
import re
import json
import time
import logging
import concurrent.futures
from ..config import settings

logger = logging.getLogger(__name__)
_client = None

# Limite de chamadas LLM por livro (evita timeout/rate-limit no Groq free tier)
MAX_LLM_BLOCKS = 40
GROQ_TIMEOUT = 25  # segundos por chamada


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

_VERB_EMOTION: dict[str, str] = {
    "gritou": "angry", "berrou": "shouting", "rosnou": "angry", "vociferou": "angry",
    "chorou": "crying", "soluçou": "crying",
    "murmurou": "whispering", "sussurrou": "whispering", "cochichou": "whispering",
    "exclamou": "surprised", "riu": "happy", "gargalhou": "happy",
    "tremeu": "fearful", "gaguejou": "fearful",
    "suplicou": "sad", "implorou": "sad",
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


def _detect_emotion(text: str, context: str = "") -> str:
    combined = (text + " " + context).lower()
    for verb, emotion in _VERB_EMOTION.items():
        if re.search(r'\b' + verb + r'\b', combined):
            return emotion
    if re.search(r'!{2,}', text): return "angry"
    if re.search(r'\?{2,}', text): return "surprised"
    if re.search(r'\.{3,}', text): return "suspenseful"
    return "neutral"


def _heuristic_full(
    segments: list[str], character_names: list[str]
) -> list[dict | None]:
    """
    Heurística completa com contexto vizinho E tracking do último falante.
    Cobre >80% dos casos sem LLM.
    """
    results: list[dict | None] = [None] * len(segments)
    last_speaker: str | None = None  # track de quem falou por último

    for i, seg in enumerate(segments):
        prev = segments[i - 1] if i > 0 else None
        nxt = segments[i + 1] if i < len(segments) - 1 else None

        if not _is_dialogue(seg):
            # Narração → atribui ao narrador sempre
            emotion = _detect_emotion(seg)
            results[i] = {"character_name": "Narrador", "emotion": emotion}
            # Atualiza last_speaker se narração contém atribuição
            sp = _find_speaker_in_text(seg, character_names)
            if sp:
                last_speaker = sp
            continue

        # É diálogo — tenta encontrar falante
        emotion = _detect_emotion(seg, nxt or "")

        # 1. Atribuição inline: — Texto — disse Pedro.
        speaker = _find_speaker_in_text(seg, character_names)
        if speaker:
            results[i] = {"character_name": speaker, "emotion": emotion}
            last_speaker = speaker
            continue

        # 2. Atribuição na linha seguinte
        if nxt and not _is_dialogue(nxt):
            speaker = _find_speaker_in_text(nxt, character_names)
            if speaker:
                emotion = _detect_emotion(seg, nxt)
                results[i] = {"character_name": speaker, "emotion": emotion}
                last_speaker = speaker
                continue

        # 3. Atribuição na linha anterior
        if prev and not _is_dialogue(prev):
            speaker = _find_speaker_in_text(prev, character_names)
            if speaker:
                results[i] = {"character_name": speaker, "emotion": emotion}
                last_speaker = speaker
                continue

        # 4. Alternância de diálogos — padrão comum em livros:
        #    A fala, B fala, A fala, B fala...
        #    Se o bloco anterior era diálogo de PersonagemX, este pode ser do outro
        if prev and _is_dialogue(prev) and results[i - 1] is not None:
            prev_speaker = results[i - 1]["character_name"]  # type: ignore
            # Pega o próximo personagem diferente do anterior
            other = next(
                (n for n in character_names if n != prev_speaker and n != "Narrador"),
                None,
            )
            if other and len([n for n in character_names if n != "Narrador"]) == 2:
                # Só aplica alternância automática se há exatamente 2 personagens
                results[i] = {"character_name": other, "emotion": emotion}
                last_speaker = other
                continue

        # 5. Mantém último falante conhecido (melhor que ir ao LLM)
        if last_speaker and last_speaker != "Narrador":
            results[i] = {"character_name": last_speaker, "emotion": emotion}
            continue

        # Não resolvido → marca para LLM
        results[i] = None

    return results


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


def _multi_section_sample(text: str, section_size: int = 3000) -> list[str]:
    sections, n = [], len(text)
    sections.append(text[:section_size])
    if n > section_size * 2:
        mid = n // 2
        sections.append(text[mid - section_size // 2:mid + section_size // 2])
    if n > section_size * 3:
        sections.append(text[n - section_size:])
    return sections


CHARACTER_EXTRACTION_PROMPT = """Analise o texto literário e identifique TODOS os personagens.

{hint}

JSON (sem markdown):
{{
  "characters": [
    {{"name":"Nome","description":"1-2 frases","gender":"male|female|neutral",
      "age_group":"child|teen|adult|elderly","personality":"hero|villain|narrator|secondary|other",
      "is_narrator":false,"appearance_order":1}}
  ]
}}

REGRAS: inclua sempre "Narrador" (is_narrator:true), procure quem fala após travessões (—).
Máximo 20 personagens.

TEXTO: {text}"""


def _call_groq_with_timeout(messages, max_tokens=2500, temperature=0.1):
    """Chama o Groq com timeout via ThreadPoolExecutor."""
    def _call():
        return _get_client().chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_call)
        return future.result(timeout=GROQ_TIMEOUT)


def extract_characters(text: str) -> list[dict]:
    regex_names = _prescan_dialogue_names(text)
    logger.info(f"Pré-scan: {len(regex_names)} nomes — {regex_names[:10]}")
    sections = _multi_section_sample(text, 3000)
    combined = "\n\n[...]\n\n".join(sections)
    hint = f"Nomes em diálogos: {', '.join(regex_names[:20])}" if regex_names else ""

    try:
        resp = _call_groq_with_timeout(
            [{"role": "user", "content": CHARACTER_EXTRACTION_PROMPT.format(
                text=combined, hint=hint)}],
            max_tokens=2500,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        characters = data.get("characters", [])
        logger.info(f"Personagens: {[c.get('name') for c in characters]}")

        if not any(c.get("is_narrator") for c in characters):
            characters.insert(0, _default_narrator())

        if not [c for c in characters if not c.get("is_narrator")] and regex_names:
            characters = [_default_narrator()]
            for i, name in enumerate(regex_names[:10], 1):
                characters.append({"name": name, "description": "Personagem",
                    "gender": "neutral", "age_group": "adult", "personality": "secondary",
                    "is_narrator": False, "appearance_order": i})

        for i, c in enumerate(characters):
            c["appearance_order"] = i
        return characters

    except concurrent.futures.TimeoutError:
        logger.error(f"Groq timeout na extração de personagens")
    except Exception as e:
        logger.error(f"Erro extract_characters: {e}")

    # Fallback regex
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
    """
    Análise de falantes com heurística máxima + LLM limitado.
    
    Estratégia:
    1. Heurística cobre narração (100%) e diálogos com atribuição explícita (~70%)
    2. Alternância automática para livros com 2 personagens
    3. LLM apenas para os restantes, máximo MAX_LLM_BLOCKS blocos
    4. O que sobrar → fallback inteligente (último falante ou narrador)
    """
    results = _heuristic_full(segments, character_names)

    unknown = [i for i, r in enumerate(results) if r is None]
    heuristic_count = len(segments) - len(unknown)
    logger.info(f"Heurística resolveu {heuristic_count}/{len(segments)} blocos. "
                f"{len(unknown)} para LLM (cap: {MAX_LLM_BLOCKS})")

    if not unknown:
        return results  # type: ignore

    # Cap de blocos para LLM — evita timeout e rate limit
    llm_indices = unknown[:MAX_LLM_BLOCKS]
    skipped = unknown[MAX_LLM_BLOCKS:]

    # Blocos acima do cap → fallback sem LLM
    for idx in skipped:
        seg = segments[idx]
        if _is_dialogue(seg):
            # Usa último falante conhecido
            last = next(
                (results[j]["character_name"] for j in range(idx - 1, -1, -1)
                 if results[j] and results[j]["character_name"] != "Narrador"),
                character_names[1] if len(character_names) > 1 else "Narrador",
            )
            results[idx] = {"character_name": last, "emotion": _detect_emotion(seg)}
        else:
            results[idx] = {"character_name": "Narrador", "emotion": "neutral"}

    # Chama LLM apenas para os blocos dentro do cap
    BATCH_PROMPT = """Rádio-novela: para cada bloco [N], identifique falante e emoção.

Personagens: {character_names}

REGRAS:
- Bloco com — ou aspas = fala de personagem (não narrador)
- Atribuição ("disse X") pode estar no CONTEXTO_ANTES ou CONTEXTO_DEPOIS
- Narração/descrição = "Narrador"
- character_name EXATAMENTE igual ao da lista
- {count} resultados na ordem

EMOÇÕES: neutral, happy, sad, angry, fearful, surprised, romantic, suspenseful, whispering, crying, shouting

{blocks}

JSON: {{"results":[{{"character_name":"nome","emotion":"emoção"}}]}}"""

    for batch_start in range(0, len(llm_indices), batch_size):
        batch = llm_indices[batch_start:batch_start + batch_size]
        block_lines = []
        for rank, idx in enumerate(batch, 1):
            prev_ctx = segments[idx - 1][:100] if idx > 0 else "(início)"
            next_ctx = segments[idx + 1][:100] if idx < len(segments) - 1 else "(fim)"
            block_lines.append(
                f"[{rank}] CONTEXTO_ANTES: {prev_ctx}\n"
                f"[{rank}] BLOCO: {segments[idx][:400]}\n"
                f"[{rank}] CONTEXTO_DEPOIS: {next_ctx}"
            )

        try:
            # Pequena pausa para respeitar rate limit do Groq free tier
            time.sleep(1.5)

            resp = _call_groq_with_timeout(
                [{"role": "user", "content": BATCH_PROMPT.format(
                    character_names=", ".join(character_names),
                    count=len(batch),
                    blocks="\n\n".join(block_lines),
                )}],
                max_tokens=800,
                temperature=0.1,
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            llm_res = data.get("results", [])

            valid_emotions = {"neutral", "happy", "excited", "sad", "angry", "fearful",
                              "surprised", "romantic", "suspenseful", "whispering",
                              "crying", "shouting"}

            for rank, idx in enumerate(batch):
                if rank < len(llm_res):
                    r = llm_res[rank]
                    char = r.get("character_name", "Narrador")
                    if char not in character_names:
                        char = next(
                            (n for n in character_names
                             if n.split()[0].lower() == char.lower()),
                            "Narrador",
                        )
                    emotion = r.get("emotion", "neutral")
                    if emotion not in valid_emotions:
                        emotion = "neutral"
                    results[idx] = {"character_name": char, "emotion": emotion}
                else:
                    results[idx] = {"character_name": "Narrador", "emotion": "neutral"}

        except concurrent.futures.TimeoutError:
            logger.warning(f"Groq timeout no batch {batch_start} — usando fallback")
            for idx in batch:
                if results[idx] is None:
                    seg = segments[idx]
                    char = "Narrador"
                    if _is_dialogue(seg) and len(character_names) > 1:
                        char = next(
                            (results[j]["character_name"] for j in range(idx - 1, -1, -1)
                             if results[j] and results[j]["character_name"] != "Narrador"),
                            character_names[1],
                        )
                    results[idx] = {"character_name": char, "emotion": _detect_emotion(seg)}

        except Exception as e:
            logger.warning(f"Erro Groq batch {batch_start}: {e}")
            for idx in batch:
                if results[idx] is None:
                    seg = segments[idx]
                    char = "Narrador" if not _is_dialogue(seg) else (
                        character_names[1] if len(character_names) > 1 else "Narrador"
                    )
                    results[idx] = {"character_name": char, "emotion": _detect_emotion(seg)}

    # Garante que não há None
    for i in range(len(results)):
        if results[i] is None:
            results[i] = {"character_name": "Narrador", "emotion": "neutral"}

    # Log distribuição final
    from collections import Counter
    dist = Counter(r["character_name"] for r in results)  # type: ignore
    logger.info(f"Distribuição final: {dict(dist)}")

    return results  # type: ignore


def _default_narrator() -> dict:
    return {
        "name": "Narrador", "description": "Voz narrativa da história",
        "gender": "neutral", "age_group": "adult",
        "personality": "narrator", "is_narrator": True, "appearance_order": 0,
    }
