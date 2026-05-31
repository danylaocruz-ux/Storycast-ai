from sqlalchemy import String, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class AudioSegment(Base):
    __tablename__ = "audio_segments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id", ondelete="SET NULL"), nullable=True, index=True)

    # Posição no livro
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chapter: Mapped[int] = mapped_column(Integer, default=1)

    # Conteúdo
    text: Mapped[str] = mapped_column(Text, nullable=False)
    emotion: Mapped[str] = mapped_column(String(50), default="neutral")
    # neutral, happy, sad, angry, fearful, surprised, romantic, suspenseful

    # Áudio gerado
    audio_path: Mapped[str] = mapped_column(String(500), nullable=True)
    duration: Mapped[float] = mapped_column(Float, default=0.0)  # segundos

    # Status da geração
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | generating | ready | error

    # Relacionamentos
    book: Mapped["Book"] = relationship(back_populates="audio_segments")  # noqa
    character: Mapped["Character"] = relationship(back_populates="audio_segments")  # noqa
