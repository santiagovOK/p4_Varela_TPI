"""Schemas SQLModel (DTOs) para el módulo de Autenticación.

Consigna TPI (docs/consignas_tpi.md):
- POST /api/v1/auth/register: entrada UserCreate y salida UserPublic (7 campos).
- POST /api/v1/auth/token: respuesta 200 {"message": "Login exitoso"} (sin exponer JWT).
- POST /api/v1/auth/logout: respuesta 200 cerrando sesión.
- GET /api/v1/auth/me: salida UserPublic (7 campos).
- Criterio 4: Autenticación y usuarios.
"""

from sqlmodel import SQLModel

from app.modules.usuarios.schemas import UserCreate, UserPublic


class LoginMessage(SQLModel):
    """DTO de respuesta para inicio de sesión exitoso (no expone el JWT)."""

    message: str = "Login exitoso"


class LogoutMessage(SQLModel):
    """DTO de respuesta para cierre de sesión."""

    message: str = "Sesión cerrada"


TokenMessage = LoginMessage

__all__ = [
    "LoginMessage",
    "LogoutMessage",
    "TokenMessage",
    "UserCreate",
    "UserPublic",
]
