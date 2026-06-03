from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from .config import settings


# SQLite: habilita WAL mode e foreign keys
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG,
)

if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    from .models import user, book, character, audio_segment, reading_session, bookmark  # noqa
    Base.metadata.create_all(bind=engine)
    # Adiciona coluna file_content se não existir (compatibilidade com DB existente)
    try:
        with engine.connect() as conn:
            if "postgresql" in settings.DATABASE_URL:
                conn.execute(__import__('sqlalchemy').text(
                    "ALTER TABLE books ADD COLUMN IF NOT EXISTS file_content BYTEA"
                ))
            else:
                # SQLite não suporta IF NOT EXISTS no ADD COLUMN
                try:
                    conn.execute(__import__('sqlalchemy').text(
                        "ALTER TABLE books ADD COLUMN file_content BLOB"
                    ))
                except Exception:
                    pass  # coluna já existe
            conn.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Migration file_content: {e}")
