from sqlalchemy import String, ForeignKey, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Atributos inferidos pela IA para seleção de voz
    gender: Mapped[str] = mapped_column(String(20), default="neutral")   # male, female, neutral
    age_group: Mapped[str] = mapped_column(String(20), default="adult")  # child, teen, adult, elderly
    personality: Mapped[str] = mapped_column(String(100), nullable=True) # hero, villain, narrator...
    is_narrator: Mapped[bool] = mapped_column(default=False)

    # ElevenLabs voice_id atribuído
    voice_id: Mapped[str] = mapped_column(String(100), nullable=True)
    voice_name: Mapped[str] = mapped_column(String(100), nullable=True)

    # Cor visual para identificação no player
    color: Mapped[str] = mapped_column(String(10), default="#7C3AED")

    # Ordem de aparição no livro (para exibição)
    appearance_order: Mapped[int] = mapped_column(Integer, default=0)

    # Relacionamentos
    book: Mapped["Book"] = relationship(back_populates="characters")  # noqa
    audio_segments: Mapped[list["AudioSegment"]] = relationship(back_populates="character")  # noqa
