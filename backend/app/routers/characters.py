from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.user import User
from ..models.book import Book
from ..models.character import Character
from ..schemas.character import CharacterResponse, CharacterUpdate
from ..utils.auth import get_current_user
from ..services.voice_assigner import list_available_voices

router = APIRouter(tags=["characters"])

# ── Rota fora do prefixo /books/{book_id} para evitar conflito com /{char_id} ─

@router.get("/voices/available")
def available_voices(current_user: User = Depends(get_current_user)):
    """Lista vozes disponíveis do ElevenLabs para atribuição manual."""
    return list_available_voices()


# ── Rotas de personagens ───────────────────────────────────────────────────────

@router.get("/books/{book_id}/characters", response_model=list[CharacterResponse])
def list_characters(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_owns_book(db, book_id, current_user.id)
    return (
        db.query(Character)
        .filter(Character.book_id == book_id)
        .order_by(Character.appearance_order)
        .all()
    )


@router.get("/books/{book_id}/characters/{char_id}", response_model=CharacterResponse)
def get_character(
    book_id: int,
    char_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_owns_book(db, book_id, current_user.id)
    return _get_char(db, book_id, char_id)


@router.put("/books/{book_id}/characters/{char_id}", response_model=CharacterResponse)
def update_character(
    book_id: int,
    char_id: int,
    payload: CharacterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_owns_book(db, book_id, current_user.id)
    char = _get_char(db, book_id, char_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(char, field, value)
    db.commit()
    db.refresh(char)
    return char


# ── Helpers ───────────────────────────────────────────────────────────────────

def _assert_owns_book(db: Session, book_id: int, user_id: int) -> None:
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Livro não encontrado")


def _get_char(db: Session, book_id: int, char_id: int) -> Character:
    char = db.query(Character).filter(
        Character.id == char_id, Character.book_id == book_id
    ).first()
    if not char:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return char
