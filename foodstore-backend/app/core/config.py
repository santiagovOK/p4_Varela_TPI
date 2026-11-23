"""Validación única de la configuración de la aplicación.

Consigna TPI (docs/consignas_tpi.pdf):
- Componentes del núcleo (app/core/config.py): Settings con pydantic-settings.
- Variables de entorno (.env) y CE-03: DATABASE_URL, SECRET_KEY, ALGORITHM,
  ACCESS_TOKEN_EXPIRE_MINUTES y FRONTEND_ORIGIN.
- Criterio 1: Backend: estructura y configuración.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de configuración de la aplicación; el entorno tiene prioridad sobre .env."""

    DATABASE_URL: str = Field(min_length=1)
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = Field(default="HS256", min_length=1)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)
    FRONTEND_ORIGIN: str = Field(default="http://localhost:5173", min_length=1)
    COOKIE_SECURE: bool | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        hide_input_in_errors=True,
    )

    @field_validator("DATABASE_URL", "ALGORITHM", "FRONTEND_ORIGIN")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("La variable de configuración no puede estar vacía")
        return stripped

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 32:
            raise ValueError("SECRET_KEY debe tener al menos 32 caracteres")
        return stripped

    @field_validator("FRONTEND_ORIGIN")
    @classmethod
    def frontend_origin_must_not_be_wildcard(cls, value: str) -> str:
        if value == "*":
            raise ValueError("FRONTEND_ORIGIN no puede ser '*'")
        return value

    @property
    def cookie_secure(self) -> bool:
        """Determina el flag `secure` de la cookie HttpOnly:
        usa COOKIE_SECURE si fue explícitamente definido; de lo contrario,
        es True cuando FRONTEND_ORIGIN usa https:// y False en http:// local.
        """
        if self.COOKIE_SECURE is not None:
            return self.COOKIE_SECURE
        return self.FRONTEND_ORIGIN.lower().startswith("https://")


@lru_cache
def get_settings() -> Settings:
    """Carga configuración explícita y cacheada para el proceso."""
    return Settings()


settings: Settings = get_settings()
