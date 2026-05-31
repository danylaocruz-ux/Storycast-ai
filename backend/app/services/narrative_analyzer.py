"""
Motor de Análise Narrativa.
Usa GPT-4o-mini para:
  - Identificar personagens
  - Atribuir falas a personagens
  - Detectar emoções por segmento
"""
import json
import re
import logging
from ..config import settings

logger = logging.getLogger(__name__)
_client = None


def _get_client():
    """Inicialização lazy do cliente OpenAI para não falhar no import sem chave."""
    global _client
    if _client is None:
        from openai import OpenAI
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY não configurada no .env")
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


# ── Extração de personagens ───────────────────────────────────────────────────

CHARACTER_EXTRACTION_PROMPT = """
Você é um analista literário especialista em identificar personagens de narrativas.

Dado o trecho abaixo, identifique TODOS os personagens mencionados, incluindo o narrador.
Retorne um JSON com a seguinte estrutura (sem markdown, apenas JSON puro):
{{
  "characters": [
    {{
      "name": "Nome do personagem",
      "description": "Breve descrição (1-2 frases)",
      "gender": "male | female | neutral",
      "age_group": "child | teen | adult | elderly",
      "personality": "hero | villain | narrator | secondary | other",
      "is_narrator": true | false,
      "appearance_order": 0
    }}
  ]
}}

Regras:
- Sempre inclua "Narrador" como primeiro personagem (is_narrator: true)
- Ordene por ordem de aparição (appearance_order começa em 0)
- Não duplique personagens
- Se um personagem não tiver gênero claro, use "neutral"
- Limite a 20 personagens mais importantes

TEXTO:
{text}
"""


def extract_characters(text: str) -> list[dict]:
    """Extrai personagens do texto completo (primeiros 8000 chars)."""
    sample = text[:8000]
    try:
        resp = _get_client().chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "user", "content": CHARACTER_EXTRACTION_PROMPT.format(text=sample)}
            ],
            temperature=0.2,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        characters = data.get("characters", [])
        # Garante que há sempre um narrador
        has_narrator = any(c.get("is_narrator") for c in characters)
        if not has_narrator:
            characters.insert(0, {
                "name": "Narrador",
                "description": "Voz narrativa da história",
                "gender": "neutral",
                "age_group": "adult",
                "personality": "narrator",
                "is_narrator": True,
                "appearance_order": 0,
            })
            # Reajusta orders
            for i, c in enumerate(characters):
                c["appearance_order"] = i
        return characters
    except Exception as e:
        logger.error(f"Erro ao extrair personagens: {e}")
        return [_default_narrator()]


# ── Análise de segmentos ──────────────────────────────────────────────────────

SEGMENT_ANALYSIS_PROMPT = """
Analise o trecho de texto abaixo e retorne um JSON (sem markdown):
{{
  "character_name": "nome exato do personagem que fala ou narra este trecho",
  "emotion": "neutral | happy | sad | angry | fearful | surprised | romantic | suspenseful"
}}

Personagens disponíveis: {character_names}

Regras:
- Se for narração, use "Narrador"
- Escolha a emoção dominante do trecho
- Retorne apenas JSON, sem explicações

TRECHO:
{text}
"""


def analyze_segment(text: str, character_names: list[str]) -> dict:
    """
    Analisa um segmento e retorna o personagem e emoção.
    Retorna dict com 'character_name' e 'emotion'.
    """
    names_str = ", ".join(character_names)
    try:
        resp = _get_client().chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "user", "content": SEGMENT_ANALYSIS_PROMPT.format(
                    character_names=names_str,
                    text=text[:600],
                )}
            ],
            temperature=0.1,
            max_tokens=80,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        char = data.get("character_name", "Narrador")
        # Valida se o personagem existe; senão usa Narrador
        if char not in character_names:
            char = "Narrador"
        return {
            "character_name": char,
            "emotion": data.get("emotion", "neutral"),
        }
    except Exception as e:
        logger.warning(f"Falha análise segmento: {e}")
        return {"character_name": "Narrador", "emotion": "neutral"}


def analyze_segments_batch(
    segments: list[str], character_names: list[str], batch_size: int = 10
) -> list[dict]:
    """Analisa múltiplos segmentos em lote para reduzir chamadas à API."""
    results = []

    BATCH_PROMPT = """
Analise cada trecho numerado abaixo e retorne um JSON com lista de resultados:
{{
  "results": [
    {{"character_name": "...", "emotion": "..."}},
    ...
  ]
}}

Personagens disponíveis: {character_names}
Para narração use "Narrador". Emotions: neutral, happy, sad, angry, fearful, surprised, romantic, suspenseful.

TRECHOS:
{segments}
"""
    for i in range(0, len(segments), batch_size):
        batch = segments[i:i + batch_size]
        numbered = "\n\n".join(f"[{j+1}] {s[:400]}" for j, s in enumerate(batch))
        try:
            resp = _get_client().chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "user", "content": BATCH_PROMPT.format(
                        character_names=", ".join(character_names),
                        segments=numbered,
                    )}
                ],
                temperature=0.1,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
            batch_results = data.get("results", [])
            # Valida e preenche resultados faltando
            for k, seg in enumerate(batch):
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
