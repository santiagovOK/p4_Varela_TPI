"""Módulo de Autenticación (`/api/v1/auth/*`) para Food Store."""

from app.modules.auth.router import ACCESS_COOKIE_NAME, get_auth_service, router
from app.modules.auth.schemas import LoginMessage, LogoutMessage, TokenMessage
from app.modules.auth.service import (
    AuthService,
    CredencialesInvalidas,
    CuentaDesactivada,
    UsuarioDuplicado,
)

__all__ = [
    "ACCESS_COOKIE_NAME",
    "AuthService",
    "CredencialesInvalidas",
    "CuentaDesactivada",
    "LoginMessage",
    "LogoutMessage",
    "TokenMessage",
    "UsuarioDuplicado",
    "get_auth_service",
    "router",
]
