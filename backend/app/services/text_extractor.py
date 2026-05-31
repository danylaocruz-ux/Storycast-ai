"""
Serviço de extração de texto.
Suporta: PDF, EPUB, DOCX, TXT
Preparado para: MOBI, RTF, OCR (imagens)
"""
import re
from pathlib import Path
from typing import Optional


def extract_text(file_path: str, fmt: str) -> str:
    """Extrai texto bruto do arquivo conforme o formato."""
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
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n\n".join(pages)


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
        text = soup.get_text(separator="\n")
        chapters.append(text)
    return "\n\n".join(chapters)


def _extract_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _extract_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def clean_text(text: str) -> str:
    """Limpa o texto extraído para processamento."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def split_into_chunks(text: str, max_chars: int = 1800) -> list[str]:
    """
    Divide o texto em chunks maiores para reduzir chamadas TTS.
    Chunks maiores = menos resets de prosódia = áudio mais natural.

    Estratégia:
    1. Tenta agrupar parágrafos completos até atingir max_chars
    2. Só divide no meio de um parágrafo se ele for muito longo
    3. Divisões sempre no fim de frases completas (.!?)
    """
    # Divide por parágrafos primeiro
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        # Parágrafo cabe no chunk atual
        if len(current) + len(para) + 2 <= max_chars:
            current = f"{current}\n\n{para}".strip() if current else para
        else:
            # Salva chunk atual se não estiver vazio
            if current:
                chunks.append(current)
                current = ""
            # Parágrafo maior que max_chars → divide por sentenças
            if len(para) > max_chars:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= max_chars:
                        current = f"{current} {sent}".strip() if current else sent
                    else:
                        if current:
                            chunks.append(current)
                        # Sentença gigante: força divisão por palavras
                        if len(sent) > max_chars:
                            words = sent.split()
                            current = ""
                            for w in words:
                                if len(current) + len(w) + 1 <= max_chars:
                                    current = f"{current} {w}".strip()
                                else:
                                    if current:
                                        chunks.append(current)
                                    current = w
                        else:
                            current = sent
            else:
                current = para

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]


def detect_language(text: str) -> str:
    """Detecção simples de idioma por frequência de palavras comuns."""
    sample = text[:2000].lower()
    pt_words = sum(sample.count(w) for w in [" de ", " e ", " que ", " para ", " não ", " em ", " uma "])
    en_words = sum(sample.count(w) for w in [" the ", " and ", " that ", " for ", " not ", " in ", " an "])
    es_words = sum(sample.count(w) for w in [" de ", " y ", " que ", " para ", " no ", " en ", " una "])

    scores = {"pt": pt_words, "en": en_words, "es": es_words}
    return max(scores, key=lambda k: scores[k])
