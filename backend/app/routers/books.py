import threading
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from ..database import get_db, SessionLocal
from ..models.user import User
from ..models.book import Book
from ..models.reading_session import ReadingSession
from ..schemas.book import (
    BookResponse, BookListResponse, BookUpdate,
    BookStatusResponse, PlayerStateResponse, PlayerStateUpdate,
)
from ..utils.auth import get_current_user
from ..utils.file_storage import validate_file, save_upload, delete_file
from ..services.book_processor import process_book

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=list[BookListResponse])
def list_books(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Book)
        .filter(Book.user_id == current_user.id)
        .order_by(Book.created_at.desc())
        .all()
    )


@router.post("", response_model=BookResponse, status_code=201)
async def upload_book(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fmt = validate_file(file)
    file_path, file_size = await save_upload(file, subfolder="books")

    # Tenta extrair título do nome do arquivo
    raw_name = file.filename or "Livro Sem Título"
    title = raw_name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()

    book = Book(
        user_id=current_user.id,
        title=title,
        format=fmt,
        file_path=file_path,
        file_size=file_size,
        status="pending",
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    # Inicia processamento em thread separada para não bloquear a resposta
    book_id = book.id
    def _run():
        session = SessionLocal()
        try:
            process_book(book_id, session)
        finally:
            session.close()

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return book


@router.get("/{book_id}", response_model=BookResponse)
def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = _get_user_book(db, book_id, current_user.id)
    return book


@router.put("/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    payload: BookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = _get_user_book(db, book_id, current_user.id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(book, field, value)
    db.commit()
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=204)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = _get_user_book(db, book_id, current_user.id)
    # Remove arquivos do disco
    delete_file(book.file_path)
    for seg in book.audio_segments:
        if seg.audio_path:
            delete_file(seg.audio_path)
    db.delete(book)
    db.commit()


@router.get("/{book_id}/status", response_model=BookStatusResponse)
def get_book_status(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = _get_user_book(db, book_id, current_user.id)
    return BookStatusResponse(
        id=book.id,
        status=book.status,
        progress=book.progress,
        status_message=book.status_message,
        total_segments=book.total_segments,
        total_duration=book.total_duration,
    )


@router.get("/{book_id}/player-state", response_model=PlayerStateResponse)
def get_player_state(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_user_book(db, book_id, current_user.id)  # valida ownership
    session = (
        db.query(ReadingSession)
        .filter(ReadingSession.user_id == current_user.id, ReadingSession.book_id == book_id)
        .first()
    )
    if not session:
        session = ReadingSession(user_id=current_user.id, book_id=book_id)
        db.add(session)
        db.commit()
        db.refresh(session)
    return session


@router.put("/{book_id}/player-state", response_model=PlayerStateResponse)
def update_player_state(
    book_id: int,
    payload: PlayerStateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_user_book(db, book_id, current_user.id)
    session = (
        db.query(ReadingSession)
        .filter(ReadingSession.user_id == current_user.id, ReadingSession.book_id == book_id)
        .first()
    )
    if not session:
        session = ReadingSession(user_id=current_user.id, book_id=book_id)
        db.add(session)

    session.current_segment = payload.current_segment
    session.current_position = payload.current_position
    if payload.playback_speed is not None:
        session.playback_speed = payload.playback_speed
    db.commit()
    db.refresh(session)
    return session


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_user_book(db: Session, book_id: int, user_id: int) -> Book:
    book = (
        db.query(Book)
        .filter(Book.id == book_id, Book.user_id == user_id)
        .first()
    )
    if not book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    return book
