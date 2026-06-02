"""
Motor de Análise Narrativa usando Groq (gratuito).
Modelos: llama-3.1-8b-instant (rápido) ou llama-3.3-70b-versatile (qualidade).
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
            raise RuntimeError("GROQ_API_KEY não configurada. Obtenha gratuitamente em groq.com")
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


# ── Heurísticas de diálogo ────────────────────────────────────────────────────

_SPEECH_VERBS = (
    r"(?:disse|falou|respondeu|perguntou|exclamou|murmurou|gritou|sussurrou|"
    r"completou|continuou|acrescentou|interrompeu|replicou|ordenou|pediu|"
    r"chamou|berrou|cochichou|afirmou|negou|concordou|discordou|admitiu|"
    r"confessou|explicou|anunciou|declarou|suplicou|implorou|resmungou)"
)
_NAME_PATTERN = r"([A-ZÁÉÍÓÚÂÊÔÃÕÜ][a-záéíóúâêôãõü]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÜ][a-záéíóúâêôãõü]+)?)"


def _is_dialogue(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith(("—", "–", '"', "“", "”"))


def _find_speaker(text: str, character_names: list[str]) -> str | None:
    for m in re.findall(_SPEECH_VERBS + r"\s+" + _NAME_PATTERN, text, re.IGNORECASE):
        candidate = m[-1] if isinstance(m, tuple) else m
        for char_name in character_names:
            if candidate.lower() in (char_name.lower(), char_name.split()[0].lower()):
                return char_name

    for m in re.findall(_NAME_PATTERN + r"\s+" + _SPEECH_VERBS, text, re.IGNORECASE):
        candidate = m[0] if isinstance(m, tuple) else m
        for char_name in character_names:
            if candidate.lower() in (char_name.lower(), char_name.split()[0].lower()):
                return char_name

    return None


def _heuristic_analysis(text: str, character_names: list[str]) -> dict | None:
    if not _is_dialogue(text):
        return None
    speaker = _find_speaker(text, character_names)
    if speaker:
        return {"character_name": speaker, "emotion": "neutral"}
    return None


# ── Pré-scan de nomes por regex (sem LLM) ────────────────────────────────────

def _prescan_dialogue_names(text: str) -> list[str]:
    """
    Extrai nomes próprios que aparecem logo após verbos de fala no texto.
    Retorna lista de nomes únicos encontrados.
    """
    found: set[str] = set()

    # verbo + Nome
    for m in re.findall(_SPEECH_VERBS + r"\s+" + _NAME_PATTERN, text, re.IGNORECASE):
        name = m[-1] if isinstance(m, tuple) else m
        if len(name) >= 3 and not name.lower() in ("disse", "falou", "não", "sim"):
            found.add(name)

    # Nome + verbo (padrão invertido)
    for m in re.findall(_NAME_PATTERN + r"\s+" + _SPEECH_VERBS, text, re.IGNORECASE):
        name = m[0] if isinstance(m, tuple) else m
        if len(name) >= 3 and not name.lower() in ("disse", "falou", "não", "sim"):
            found.add(name)

    # Diálogos com travessão seguido por nome (— Texto — disse Nome)
    for m in re.findall(r"—[^—\n]{5,80}—\s*" + _SPEECH_VERBS + r"\s+" + _NAME_PATTERN, text):
        pass  # já coberto pelos padrões acima

    return sorted(found)


def _multi_section_sample(text: str, section_size: int = 3500) -> list[str]:
    """Retorna amostras do início, meio e fim do texto."""
    sections = []
    n = len(text)
    sections.append(text[:section_size])
    if n > section_size * 2:
        mid = n // 2
        sections.append(text[max(0, mid - section_size // 2):mid + section_size // 2])
    if n > section_size * 3:
        sections.append(text[max(0, n - section_size):])
    return sections


# ── Extração de personagens ───────────────────────────────────────────────────

CHARACTER_EXTRACTION_PROMPT = """Você é um analista literário especialista. Analise o trecho do livro e identifique TODOS os personagens.

{hint}

Retorne APENAS este JSON (sem markdown):
{{
  "characters": [
    {{
      "name": "Nome",
      "description": "1-2 frases descrevendo o personagem",
      "gender": "male | female | neutral",
      "age_group": "child | teen | adult | elderly",
      "personality": "hero | villain | narrator | secondary | other",
      "is_narrator": false,
      "appearance_order": 1
    }}
  ]
}}

REGRAS OBRIGATÓRIAS:
1. SEMPRE inclua "Narrador" como primeiro item (is_narrator: true, appearance_order: 0)
2. Identifique personagens que FALAM — procure travessões (—) e verbos de fala: disse, falou, respondeu, perguntou, exclamou...
3. Todo nome próprio que aparece em cenas de diálogo é um personagem candidato
4. Não duplique personagens (ex: "João" e "João Silva" são o mesmo)
5. Máximo 20 personagens
6. Se encontrar apenas narração sem personagens, ainda assim retorne pelo menos o Narrador

TEXTO (pode ter múltiplas seções do livro):
{text}
"""


def extract_characters(text: str) -> list[dict]:
    """Extrai personagens usando múltiplas seções + pré-scan por regex."""
    # Pré-scan rápido por regex
    regex_names = _prescan_dialogue_names(text)
    logger.info(f"Pré-scan encontrou {len(regex_names)} nomes: {regex_names[:10]}")

    # Amostras de múltiplas seções para melhor cobertura
    sections = _multi_section_sample(text, section_size=3000)
    combined = "\n\n[...]\n\n".join(sections)

    hint = ""
    if regex_names:
        hint = f"Dica: Os seguintes nomes foram detectados em padrões de diálogo no texto: {', '.join(regex_names[:20])}\nVerifique se são personagens e inclua os relevantes."

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

        # Garante que o narrador existe
        has_narrator = any(c.get("is_narrator") for c in characters)
        if not has_narrator:
            characters.insert(0, _default_narrator())

        # Se LLM só retornou narrador mas regex encontrou nomes, cria personagens a partir deles
        if len([c for c in characters if not c.get("is_narrator")]) == 0 and regex_names:
            logger.warning("LLM retornou apenas narrador, usando pré-scan como fallback")
            characters = [_default_narrator()]
            for i, name in enumerate(regex_names[:10], 1):
                characters.append({
                    "name": name,
                    "description": f"Personagem encontrado no livro",
                    "gender": "neutral",
                    "age_group": "adult",
                    "personality": "secondary",
                    "is_narrator": False,
                    "appearance_order": i,
                })

        for i, c in enumerate(characters):
            c["appearance_order"] = i

        return characters

    except Exception as e:
        logger.error(f"Erro ao extrair personagens: {e}")
        # Fallback total com regex
        if regex_names:
            chars = [_default_narrator()]
            for i, name in enumerate(regex_names[:10], 1):
                chars.append({
                    "name": name, "description": "Personagem do livro",
                    "gender": "neutral", "age_group": "adult",
                    "personality": "secondary", "is_narrator": False,
                    "appearance_order": i,
                })
            return chars
        return [_default_narrator()]


# ── Análise de segmentos ──────────────────────────────────────────────────────

SEGMENT_ANALYSIS_PROMPT = """Analise o trecho literário e identifique QUEM está falando/narrando.

Retorne APENAS este JSON (sem markdown):
{{"character_name": "nome exato", "emotion": "neutral"}}

Personagens disponíveis: {character_names}

REGRAS:
- Se o trecho COMEÇA COM TRAVESSÃO (—) ou ASPAS, é FALA DE PERSONAGEM
- Procure verbos de fala: disse, falou, respondeu, perguntou, exclamou, murmurou...
- Verifique qual dos personagens disponíveis está falando
- Se for descrição/narração sem diálogo, use "Narrador"
- character_name deve ser EXATAMENTE um dos nomes disponíveis
- Emoções: neutral, happy, sad, angry, fearful, surprised, romantic, suspenseful

TRECHO:
{text}"""


def analyze_segment(text: str, character_names: list[str]) -> dict:
    result = _heuristic_analysis(text, character_names)
    if result:
        return result

    try:
        resp = _get_client().chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": SEGMENT_ANALYSIS_PROMPT.format(
                character_names=", ".join(character_names),
                text=text[:600],
            )}],
            temperature=0.1,
            max_tokens=80,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        char = data.get("character_name", "Narrador")
        if char not in character_names:
            char = "Narrador"
        return {"character_name": char, "emotion": data.get("emotion", "neutral")}
    except Exception as e:
        logger.warning(f"Falha análise segmento: {e}")
        return {"character_name": "Narrador", "emotion": "neutral"}


def analyze_segments_batch(
    segments: list[str], character_names: list[str], batch_size: int = 10
) -> list[dict]:
    results = []

    BATCH_PROMPT = """Analise cada trecho numerado de um livro e identifique QUEM fala ou narra cada um.

Retorne APENAS este JSON:
{{"results": [{{"character_name": "nome exato", "emotion": "neutral"}}, ...]}}

Personagens disponíveis: {character_names}

REGRAS IMPORTANTES:
1. Trechos que COMEÇAM com — (travessão) ou aspas são FALAS — identifique quem fala
2. Para identificar o falante, procure: "disse X", "falou X", "respondeu X", "perguntou X" no trecho
3. Trechos descritivos sem diálogo = "Narrador"
4. character_name deve ser EXATAMENTE um dos personagens disponíveis
5. Retorne exatamente {count} resultados na mesma ordem
6. Emoções: neutral, happy, sad, angry, fearful, surprised, romantic, suspenseful

TRECHOS:
{segments}"""

    for i in range(0, len(segments), batch_size):
        batch = segments[i:i + batch_size]
        pre_results = [_heuristic_analysis(s, character_names) for s in batch]
        unknown_indices = [j for j, r in enumerate(pre_results) if r is None]

        if not unknown_indices:
            results.extend(pre_results)
            continue

        unknown_batch = [batch[j] for j in unknown_indices]
        numbered = "\n\n".join(f"[{j+1}] {s[:500]}" for j, s in enumerate(unknown_batch))

        try:
            resp = _get_client().chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": BATCH_PROMPT.format(
                    character_names=", ".join(character_names),
                    count=len(unknown_batch),
                    segments=numbered,
                )}],
                temperature=0.1,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            llm_results = data.get("results", [])

            llm_idx = 0
            for j in range(len(batch)):
                if pre_results[j] is not None:
                    results.append(pre_results[j])
                elif llm_idx < len(llm_results):
                    r = llm_results[llm_idx]
                    char = r.get("character_name", "Narrador")
                    if char not in character_names:
                        char = "Narrador"
                    results.append({"character_name": char, "emotion": r.get("emotion", "neutral")})
                    llm_idx += 1
                else:
                    results.append({"character_name": "Narrador", "emotion": "neutral"})

        except Exception as e:
            logger.warning(f"Erro em batch {i}: {e}")
            for j in range(len(batch)):
                if pre_results[j] is not None:
                    results.append(pre_results[j])
                else:
                    results.append({"character_name": "Narrador", "emotion": "neutral"})

    return results


def _default_narrator() -> dict:
    return {
        "name": "Narrador",
        "description": "Voz narrativa da história",
        "gender": "neutral",
        "age_group": "adult",
        "personality": "narrator",
        "is_narrator": True,
        "appearance_order": 0,
    }
