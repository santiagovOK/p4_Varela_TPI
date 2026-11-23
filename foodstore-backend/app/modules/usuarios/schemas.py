"""Schemas SQLModel (DTOs) para el módulo de Usuarios.

Consigna TPI (docs/consignas_tpi.pdf):
- Schemas Usuario: `UserCreate` (registro con contraseña entre 8 y 72 caracteres/bytes
  para compatibilidad bcrypt) y `UserPublic` unificado de 7 campos (sin exponer
  `hashed_password` ni esquema dual `UserAdminPublic`).
- Criterio 2: Modelo de datos.
- Criterio 4: Autenticación y usuarios.
"""

from datetime import datetime

from pydantic import EmailStr, field_validator
from sqlmodel import Field, SQLModel


class UserCreate(SQLModel):
    """DTO de entrada para registro de un nuevo usuario."""

    username: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password_utf8_bytes(cls, value: str) -> str:
        """Valida que la contraseña no supere el límite de 72 bytes UTF-8 de bcrypt."""
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede superar los 72 bytes en UTF-8.")
        return value


class UserPublic(SQLModel):
    """DTO de salida pública unificado para usuarios (nunca incluye hashed_password)."""

    id: int
    username: str
    full_name: str
    email: str
    role: str
    disabled: bool
    created_at: datetime


__all__ = ["UserCreate", "UserPublic"]
