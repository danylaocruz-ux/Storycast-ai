from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from ..database import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=True)
    format: Mapped[str] = mapped_column(String(20), nullable=False)   # pdf, epub, docx, txt
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    cover_path: Mapped[str] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0)        # bytes

    # Metadados extraídos
    total_chars: Mapped[int] = mapped_column(Integer, default=0)
    total_segments: Mapped[int] = mapped_column(Integer, default=0)
    total_duration: Mapped[float] = mapped_column(Float, default=0.0)  # segundos
    language: Mapped[str] = mapped_column(String(10), default="pt")

    # Status do processamento
    status: Mapped[str] = mapped_column(String(30), default="pending")
    # pending | extracting | analyzing | generating_audio | ready | error
    status_message: Mapped[str] = mapped_column(Text, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)          # 0-100

    is_favorite: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    user: Mapped["User"] = relationship(back_populates="books")  # noqa
    characters: Mapped[list["Character"]] = relationship(back_populates="book", cascade="all, delete-orphan")  # noqa
    audio_segments: Mapped[list["AudioSegment"]] = relationship(back_populates="book", cascade="all, delete-orphan")  # noqa
    reading_sessions: Mapped[list["ReadingSession"]] = relationship(back_populates="book", cascade="all, delete-orphan")  # noqa
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="book", cascade="all, delete-orphan")  # noqa
