import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile, HTTPException
from ..config import settings

ALLOWED_FORMATS = {
    "application/pdf": "pdf",
    "application/epub+zip": "epub",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}
ALLOWED_EXTENSIONS = {".pdf", ".epub", ".docx", ".txt"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_file(file: UploadFile) -> str:
    """Valida e retorna o formato do arquivo."""
    ext = get_extension(file.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato não suportado: {ext}. Use: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    # Mapeia extensão -> formato
    return ext.lstrip(".")


async def save_upload(file: UploadFile, subfolder: str = "books") -> tuple[str, int]:
    """
    Salva arquivo enviado e retorna (caminho_relativo, tamanho_bytes).
    Lê em chunks para evitar estouro de memória em arquivos grandes.
    """
    ext = get_extension(file.filename or ".bin")
    filename = f"{uuid.uuid4().hex}{ext}"
    dest_dir = settings.storage_path / subfolder
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename

    total = 0
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await file.read(1024 * 1024):  # lê 1 MB por vez
            total += len(chunk)
            if total > MAX_FILE_SIZE:
                await out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Arquivo excede 100 MB")
            await out.write(chunk)

    return str(dest), total


def delete_file(path: str) -> None:
    """Remove arquivo do disco com segurança."""
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass


def get_audio_url(path: str) -> str:
    """Converte caminho local em URL relativa para o cliente."""
    return f"/static/{Path(path).name}"
