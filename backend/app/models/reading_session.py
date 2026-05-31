from sqlalchemy import Integer, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from ..database import Base


class ReadingSession(Base):
    __tablename__ = "reading_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)

    # Posição atual
    current_segment: Mapped[int] = mapped_column(Integer, default=0)
    current_position: Mapped[float] = mapped_column(Float, default=0.0)  # segundos dentro do segmento

    # Velocidade de reprodução salva pelo usuário
    playback_speed: Mapped[float] = mapped_column(Float, default=1.0)

    # Estatísticas
    total_listened: Mapped[float] = mapped_column(Float, default=0.0)  # segundos totais ouvidos

    last_played_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relacionamentos
    user: Mapped["User"] = relationship(back_populates="reading_sessions")  # noqa
    book: Mapped["Book"] = relationship(back_populates="reading_sessions")  # noqa
