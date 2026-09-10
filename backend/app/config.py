import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/esus"
    jwt_secret: str = "dev-secret-troque"
    jwt_expires_min: int = 480
    jwt_algorithm: str = "HS256"
    auto_seed: bool = True

    @field_validator("database_url", mode="before")
    @classmethod
    def _normaliza_url(cls, v: str) -> str:
        if not v:
            return v
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://"):]
        return v


settings = Settings()
PORT = int(os.environ.get("PORT", "8010"))
