"""
ReadmitIQ — Core Configuration
Config-driven via environment variables with sensible defaults.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────────────
    APP_NAME: str = "ReadmitIQ"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-256-bit-random-key"

    # ── Database ───────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://readmitiq:readmitiq@postgres:5432/readmitiq"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # ── Redis / Celery ─────────────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # ── CORS ───────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:80",
        "http://frontend:3000",
    ]

    # ── ML / Model ─────────────────────────────────────────────────────────
    MODEL_DIR: str = "/app/models"
    MODEL_REGISTRY_PATH: str = "/app/models/registry.json"
    INFERENCE_BATCH_SIZE: int = 64
    RISK_THRESHOLD_HIGH: float = 0.70
    RISK_THRESHOLD_MEDIUM: float = 0.40

    # ── SHAP ───────────────────────────────────────────────────────────────
    SHAP_MAX_DISPLAY_FEATURES: int = 15
    SHAP_BACKGROUND_SAMPLES: int = 100

    # ── Optuna ─────────────────────────────────────────────────────────────
    OPTUNA_N_TRIALS: int = 50
    OPTUNA_TIMEOUT: int = 3600  # seconds

    # ── Security / HIPAA ───────────────────────────────────────────────────
    JWT_SECRET: str = "jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 8
    ENCRYPTION_KEY: Optional[str] = None   # AES-256 key (base64)

    # ── Logging ────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"   # "json" | "text"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
