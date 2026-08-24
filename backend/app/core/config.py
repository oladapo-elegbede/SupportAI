from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory pointing to project root (supportai/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "SupportAI"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # API Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Database (PostgreSQL + pgvector)
    DATABASE_URL: str = "postgresql+asyncpg://supportai:supportai_dev@localhost:5433/supportai"

    # Redis (Job Queue Broker)
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI / LLM Configuration
    LLM_PROVIDER: str = "ollama"
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5:3b"
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # Storage Configuration
    STORAGE_PROVIDER: str = "local"
    UPLOAD_DIR: str = "./uploads"

    # Security Configuration
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
