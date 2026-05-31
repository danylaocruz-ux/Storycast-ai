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
    """Inicialização lazy do cliente Groq."""
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
    r"chamou|gritou|berrou|cochichou)"
)
_NAME_PATTERN = r"([A-ZÁÉÍÓÚÂÊÔÃÕÜ][a-záéíóúâêôãõü]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÜ][a-záéíóúâêôãõü]+)?)"


def _is_dialogue(text: str) -> bool:
    """Retorna True se o trecho parece ser diálogo (começa com travessão ou aspas)."""
    stripped = text.strip()
    return stripped.startswith(("—", "–", '"', "“", "”"))


def _find_speaker(text: str, character_names: list[str]) -> str | None:
    """
    Busca o falante usando verbos de fala no trecho.
    Ex: '— Venha cá — disse Maria.' → 'Maria'
    """
    # Padrão: verbo + Nome
    for m in re.findall(_SPEECH_VERBS + r"\s+" + _NAME_PATTERN, text):
        candidate = m if isinstance(m, str) else m
        for char_name in character_names:
            first = char_name.split()[0]
            if candidate.lower() in (char_name.lower(), first.lower()):
                return char_name

    # Padrão invertido: Nome + verbo
    for m in re.findall(_NAME_PATTERN + r"\s+" + _SPEECH_VERBS, text):
        candidate = m if isinstance(m, str) else m
        for char_name in character_names:
            first = char_name.split()[0]
            if candidate.lower() in (char_name.lower(), first.lower()):
                return char_name

    return None


def _heuristic_analysis(text: str, character_names: list[str]) -> dict | None:
    """
    Tenta identificar personagem/emoção por heurística antes de chamar o LLM.
    Retorna dict ou None se não conseguir.
    """
    if not _is_dialogue(text):
        return None  # Deixa o LLM decidir para narração

    speaker = _find_speaker(text, character_names)
    if speaker:
        return {"character_name": speaker, "emotion": "neutral"}

    # É diálogo mas não encontramos o falante — deixa o LLM decidir
    return None


# ── Extração de personagens ───────────────────────────────────────────────────

CHARACTER_EXTRACTION_PROMPT = """Você é um analista literário. Leia o trecho e identifique TODOS os personagens.

Retorne APENAS este JSON (sem markdown):
{
  "characters": [
    {
      "name": "Nome",
      "description": "1-2 frases",
      "gender": "male | female | neutral",
      "age_group": "child | teen | adult | elderly",
      "personality": "hero | villain | narrator | secondary | other",
      "is_narrator": false,
      "appearance_order": 1
    }
  ]
}

REGRAS OBRIGATÓRIAS:
- SEMPRE inclua "Narrador" como primeiro item (is_narrator: true, appearance_order: 0)
- Liste personagens que FALAM ou são PROTAGONISTAS (procure travessões — e falas)
- Não duplique personagens
- Máximo 20 personagens

TEXTO:
{text}
"""


def extract_characters(text: str) -> list[dict]:
    """Extrai personagens do texto completo (primeiros 8000 chars)."""
    sample = text[:8000]
    try:
        resp = _get_client().chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": CHARACTER_EXTRACTION_PROMPT.format(text=sample)}],
            temperature=0.2,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        characters = data.get("characters", [])
        has_narrator = any(c.get("is_narrator") for c in characters)
        if not has_narrator:
            characters.insert(0, _default_narrator())
            for i, c in enumerate(characters):
                c["appearance_order"] = i
        return characters
    except Exception as e:
        logger.error(f"Erro ao extrair personagens: {e}")
        return [_default_narrator()]


# ── Análise de segmentos ──────────────────────────────────────────────────────

SEGMENT_ANALYSIS_PROMPT = """Analise o trecho literário e identifique QUEM está falando/narrando.

Retorne APENAS este JSON (sem markdown):
{"character_name": "nome exato", "emotion": "neutral"}

Personagens disponíveis: {character_names}

REGRAS:
- Se o trecho COMEÇA COM TRAVESSÃO (—) ou ASPAS, é FALA DE PERSONAGEM — identifique quem fala
- Se é descrição/narração sem diálogo, use "Narrador"
- Procure verbos de fala: disse, falou, respondeu, perguntou, exclamou, murmurou...
- Emoções: neutral, happy, sad, angry, fearful, surprised, romantic, suspenseful

TRECHO:
{text}"""


def analyze_segment(text: str, character_names: list[str]) -> dict:
    """Analisa um segmento e retorna personagem e emoção."""
    # Heurística primeiro
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
    """Analisa múltiplos segmentos em lote, com heurística prévia."""
    results = []

    BATCH_PROMPT = """Analise cada trecho numerado de um livro e identifique o personagem que fala/narra.

Retorne APENAS este JSON:
{{"results": [{{"character_name": "nome exato", "emotion": "neutral"}}, ...]}}

Personagens disponíveis: {character_names}

REGRAS IMPORTANTES:
1. Trechos que COMEÇAM com — (travessão) ou aspas são FALAS de personagens — não use "Narrador"
2. Para identificar o falante, procure: "disse X", "falou X", "respondeu X" no trecho
3. Trechos descritivos sem diálogo = "Narrador"
4. Emoções: neutral, happy, sad, angry, fearful, surprised, romantic, suspenseful
5. Retorne exatamente {count} resultados na mesma ordem dos trechos

TRECHOS:
{segments}"""

    for i in range(0, len(segments), batch_size):
        batch = segments[i:i + batch_size]

        # Aplica heurística em cada segmento do lote
        pre_results = [_heuristic_analysis(s, character_names) for s in batch]
        unknown_indices = [j for j, r in enumerate(pre_results) if r is None]

        if not unknown_indices:
            # Todos resolvidos por heurística
            results.extend([r for r in pre_results])
            continue

        # Envia ao Groq apenas os segmentos sem resultado heurístico
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

            # Mescla resultados heurísticos e do LLM
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
