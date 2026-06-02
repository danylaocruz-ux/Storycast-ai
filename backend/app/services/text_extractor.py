"""
Serviço de extração de texto.
Suporta: PDF, EPUB, DOCX, TXT
"""
import re
from pathlib import Path


def extract_text(file_path: str, fmt: str) -> str:
    extractors = {
        "pdf": _extract_pdf,
        "epub": _extract_epub,
        "docx": _extract_docx,
        "txt": _extract_txt,
    }
    fn = extractors.get(fmt)
    if not fn:
        raise ValueError(f"Formato não suportado: {fmt}")
    return fn(file_path)


def _extract_pdf(path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(path)
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_epub(path: str) -> str:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    book = epub.read_epub(path, options={"ignore_ncx": True})
    chapters = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        chapters.append(soup.get_text(separator="\n"))
    return "\n\n".join(chapters)


def _extract_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


# ── Constantes de diálogo ────────────────────────────────────────────────────

_DIALOGUE_STARTERS = ('—', '–', '—', '–', '"', '“', '”')


def _is_dialogue_line(line: str) -> bool:
    """Retorna True se a linha é uma fala de personagem (começa com travessão/aspas)."""
    return line.lstrip().startswith(_DIALOGUE_STARTERS)


# ── Segmentação por falante ─────────────────────────────────────────────────

def split_into_speaker_blocks(text: str, max_narrative_chars: int = 500) -> list[str]:
    """
    Divide o texto em blocos por falante — LÓGICA DE RÁDIO-NOVELA.

    Regras:
    - Cada linha de diálogo (começa com —) = bloco INDIVIDUAL e exclusivo
    - Linhas de narração consecutivas são agrupadas até max_narrative_chars
    - NUNCA mistura diálogo e narração no mesmo bloco
    - NUNCA mistura falas de diferentes personagens no mesmo bloco

    Isso garante que cada bloco tenha UM ÚNICO dono (locutor).
    """
    # Divide em linhas individuais
    raw_lines = re.split(r'\n+', text)
    lines = [l.strip() for l in raw_lines if l.strip()]

    blocks: list[str] = []
    current_narrative = ""

    for line in lines:
        if _is_dialogue_line(line):
            # Salva narração acumulada antes de entrar no diálogo
            if current_narrative:
                blocks.append(current_narrative.strip())
                current_narrative = ""
            # Cada fala = bloco próprio, independente do tamanho
            blocks.append(line.strip())
        else:
            # Narração: agrupa parágrafos curtos para evitar TTS excessivamente fragmentado
            if current_narrative and len(current_narrative) + len(line) + 1 > max_narrative_chars:
                blocks.append(current_narrative.strip())
                current_narrative = line
            else:
                current_narrative = (current_narrative + " " + line).strip() if current_narrative else line

    if current_narrative:
        blocks.append(current_narrative.strip())

    # Remove blocos vazios e muito curtos (lixo do parser)
    return [b for b in blocks if b.strip() and len(b.strip()) >= 2]


def split_into_chunks(text: str, max_chars: int = 1800) -> list[str]:
    """
    Mantida para compatibilidade — use split_into_speaker_blocks para novo processamento.
    Divide por parágrafos agrupados até max_chars.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}".strip() if current else para
        else:
            if current:
                chunks.append(current)
                current = ""
            if len(para) > max_chars:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= max_chars:
                        current = f"{current} {sent}".strip() if current else sent
                    else:
                        if current:
                            chunks.append(current)
                        current = sent if len(sent) <= max_chars else sent[:max_chars]
            else:
                current = para

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]


def detect_language(text: str) -> str:
    sample = text[:2000].lower()
    pt = sum(sample.count(w) for w in [" de ", " e ", " que ", " para ", " não ", " em ", " uma "])
    en = sum(sample.count(w) for w in [" the ", " and ", " that ", " for ", " not ", " in ", " an "])
    es = sum(sample.count(w) for w in [" de ", " y ", " que ", " para ", " no ", " en ", " una "])
    return max({"pt": pt, "en": en, "es": es}, key=lambda k: {"pt": pt, "en": en, "es": es}[k])
