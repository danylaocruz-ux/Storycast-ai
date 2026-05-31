from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from ..database import get_db
from ..models.user import User
from ..models.book import Book
from ..models.audio_segment import AudioSegment
from ..models.bookmark import Bookmark
from ..schemas.audio import AudioSegmentResponse, BookmarkCreate, BookmarkResponse
from ..utils.auth import get_current_user

router = APIRouter(tags=["audio"])


# ── Segmentos de áudio ────────────────────────────────────────────────────────

@router.get("/books/{book_id}/segments", response_model=list[AudioSegmentResponse])
def list_segments(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_owns_book(db, book_id, current_user.id)
    return (
        db.query(AudioSegment)
        .filter(AudioSegment.book_id == book_id)
        .order_by(AudioSegment.segment_index)
        .all()
    )


@router.get("/books/{book_id}/segments/{segment_index}", response_model=AudioSegmentResponse)
def get_segment(
    book_id: int,
    segment_index: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_owns_book(db, book_id, current_user.id)
    seg = (
        db.query(AudioSegment)
        .filter(AudioSegment.book_id == book_id, AudioSegment.segment_index == segment_index)
        .first()
    )
    if not seg:
        raise HTTPException(status_code=404, detail="Segmento não encontrado")
    return seg


@router.get("/books/{book_id}/segments/{segment_index}/audio")
def stream_audio(
    book_id: int,
    segment_index: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Serve o arquivo de áudio do segmento."""
    _assert_owns_book(db, book_id, current_user.id)
    seg = (
        db.query(AudioSegment)
        .filter(AudioSegment.book_id == book_id, AudioSegment.segment_index == segment_index)
        .first()
    )
    if not seg:
        raise HTTPException(status_code=404, detail="Segmento não encontrado")
    if not seg.audio_path:
        raise HTTPException(status_code=404, detail="Áudio ainda não gerado")

    path = Path(seg.audio_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de áudio não encontrado no disco")

    return FileResponse(
        path=str(path),
        media_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes"},
    )


# ── Marcadores ────────────────────────────────────────────────────────────────

@router.post("/bookmarks", response_model=BookmarkResponse, status_code=201)
def create_bookmark(
    payload: BookmarkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_owns_book(db, payload.book_id, current_user.id)
    bm = Bookmark(
        user_id=current_user.id,
        book_id=payload.book_id,
        segment_index=payload.segment_index,
        position=payload.position,
        label=payload.label,
    )
    db.add(bm)
    db.commit()
    db.refresh(bm)
    return bm


@router.get("/books/{book_id}/bookmarks", response_model=list[BookmarkResponse])
def list_bookmarks(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_owns_book(db, book_id, current_user.id)
    return (
        db.query(Bookmark)
        .filter(Bookmark.book_id == book_id, Bookmark.user_id == current_user.id)
        .order_by(Bookmark.segment_index)
        .all()
    )


@router.delete("/bookmarks/{bookmark_id}", status_code=204)
def delete_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bm = (
        db.query(Bookmark)
        .filter(Bookmark.id == bookmark_id, Bookmark.user_id == current_user.id)
        .first()
    )
    if not bm:
        raise HTTPException(status_code=404, detail="Marcador não encontrado")
    db.delete(bm)
    db.commit()


# ── Helper ────────────────────────────────────────────────────────────────────

def _assert_owns_book(db: Session, book_id: int, user_id: int):
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
