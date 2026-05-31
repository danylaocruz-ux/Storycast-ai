"""
Motor de Análise Narrativa usando Groq (gratuito).
Modelos: llama-3.1-8b-instant (rápido) ou llama-3.3-70b-versatile (qualidade).
"""
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


CHARACTER_EXTRACTION_PROMPT = """
Você é um analista literário especialista em identificar personagens de narrativas.

Dado o trecho abaixo, identifique TODOS os personagens mencionados, incluindo o narrador.
Retorne um JSON com a seguinte estrutura (sem markdown, apenas JSON puro):
{
  "characters": [
    {
      "name": "Nome do personagem",
      "description": "Breve descrição (1-2 frases)",
      "gender": "male | female | neutral",
      "age_group": "child | teen | adult | elderly",
      "personality": "hero | villain | narrator | secondary | other",
      "is_narrator": true,
      "appearance_order": 0
    }
  ]
}

Regras:
- Sempre inclua "Narrador" como primeiro personagem (is_narrator: true)
- Ordene por ordem de aparição (appearance_order começa em 0)
- Não duplique personagens
- Limite a 20 personagens mais importantes

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


SEGMENT_ANALYSIS_PROMPT = """Analise o trecho e retorne JSON:
{"character_name": "nome exato do personagem ou Narrador", "emotion": "neutral | happy | sad | angry | fearful | surprised | romantic | suspenseful"}

Personagens disponíveis: {character_names}
Se for narração, use "Narrador".

TRECHO: {text}"""


def analyze_segment(text: str, character_names: list[str]) -> dict:
    """Analisa um segmento e retorna personagem e emoção."""
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
    """Analisa múltiplos segmentos em lote."""
    results = []

    BATCH_PROMPT = """Analise cada trecho numerado e retorne JSON:
{{"results": [{{"character_name": "...", "emotion": "..."}}, ...]}}

Personagens: {character_names}
Emotions: neutral, happy, sad, angry, fearful, surprised, romantic, suspenseful.
Use "Narrador" para narração.

TRECHOS:
{segments}"""

    for i in range(0, len(segments), batch_size):
        batch = segments[i:i + batch_size]
        numbered = "\n\n".join(f"[{j+1}] {s[:400]}" for j, s in enumerate(batch))
        try:
            resp = _get_client().chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": BATCH_PROMPT.format(
                    character_names=", ".join(character_names),
                    segments=numbered,
                )}],
                temperature=0.1,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            batch_results = data.get("results", [])
            for k in range(len(batch)):
                if k < len(batch_results):
                    r = batch_results[k]
                    char = r.get("character_name", "Narrador")
                    if char not in character_names:
                        char = "Narrador"
                    results.append({"character_name": char, "emotion": r.get("emotion", "neutral")})
                else:
                    results.append({"character_name": "Narrador", "emotion": "neutral"})
        except Exception as e:
            logger.warning(f"Erro em batch {i}: {e}")
            for _ in batch:
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
