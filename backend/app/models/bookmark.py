from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from ..database import Base


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)

    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[float] = mapped_column(Float, default=0.0)  # segundos
    label: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relacionamentos
    user: Mapped["User"] = relationship(back_populates="bookmarks")  # noqa
    book: Mapped["Book"] = relationship(back_populates="bookmarks")  # noqa
