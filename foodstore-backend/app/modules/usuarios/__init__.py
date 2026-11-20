"""Módulo de gestión de usuarios."""

from typing import TYPE_CHECKING, Any

from app.modules.usuarios.models import Usuario
from app.modules.usuarios.repository import UsuarioRepository
from app.modules.usuarios.schemas import UserCreate, UserPublic
from app.modules.usuarios.service import (
    AutoDesactivacionNoPermitida,
    UsuarioNoEncontrado,
    UsuarioService,
)
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork

if TYPE_CHECKING:
    from app.modules.usuarios.router import get_usuario_service, router


def __getattr__(name: str) -> Any:
    """Resuelve ``router`` y ``get_usuario_service`` bajo demanda para evitar ciclos con ``app.core.deps``."""
    if name in {"router", "get_usuario_service"}:
        from app.modules.usuarios import router as usuarios_router_module

        return getattr(usuarios_router_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AutoDesactivacionNoPermitida",
    "UserCreate",
    "UserPublic",
    "Usuario",
    "UsuarioNoEncontrado",
    "UsuarioRepository",
    "UsuarioService",
    "UsuarioUnitOfWork",
    "get_usuario_service",
    "router",
]
