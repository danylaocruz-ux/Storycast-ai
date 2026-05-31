from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from .database import create_tables
from .config import settings
from .routers import auth_router, books_router, characters_router, audio_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria tabelas na inicialização
    create_tables()
    # Garante que os diretórios de storage existem
    _ = settings.books_path
    _ = settings.audio_path
    _ = settings.covers_path
    yield


app = FastAPI(
    title="StoryCast AI",
    description="Transforma livros em experiências sonoras cinematográficas",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (permite todas as origens em dev; restrinja em produção) ─────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router, prefix="/api/v1")
app.include_router(books_router, prefix="/api/v1")
app.include_router(characters_router, prefix="/api/v1")
app.include_router(audio_router, prefix="/api/v1")

# ── Arquivos estáticos (áudios) ───────────────────────────────────────────────
app.mount("/static/audio", StaticFiles(directory=str(settings.audio_path)), name="audio")
app.mount("/static/covers", StaticFiles(directory=str(settings.covers_path)), name="covers")


@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
