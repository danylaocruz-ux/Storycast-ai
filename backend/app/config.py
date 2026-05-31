from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Segurança
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # Banco
    DATABASE_URL: str = "sqlite:///./storycast.db"

    # IA - Groq (gratuito em groq.com)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Armazenamento
    STORAGE_PATH: str = "./storage"

    # Servidor
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    @property
    def storage_path(self) -> Path:
        p = Path(self.STORAGE_PATH)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def books_path(self) -> Path:
        p = self.storage_path / "books"
        p.mkdir(exist_ok=True)
        return p

    @property
    def audio_path(self) -> Path:
        p = self.storage_path / "audio"
        p.mkdir(exist_ok=True)
        return p

    @property
    def covers_path(self) -> Path:
        p = self.storage_path / "covers"
        p.mkdir(exist_ok=True)
        return p


settings = Settings()
