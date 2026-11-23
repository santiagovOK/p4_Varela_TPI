"""Router FastAPI para gestión administrativa de usuarios (`/api/v1/admin/usuarios/*`).

Consigna TPI (docs/consignas_tpi.pdf):
- GET /api/v1/admin/usuarios -> 200 list[UserPublic] (incluye cuentas desactivadas).
- POST /api/v1/admin/usuarios/{id}/activar -> 200 UserPublic (idempotente) / 404.
- POST /api/v1/admin/usuarios/{id}/desactivar -> 200 UserPublic (idempotente) / 404 / 400 auto-desactivación.
- Todos los endpoints requieren rol ``admin`` mediante ``require_role(["admin"])``.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import require_role
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import UserPublic
from app.modules.usuarios.service import (
    AutoDesactivacionNoPermitida,
    UsuarioNoEncontrado,
    UsuarioService,
)
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork

router = APIRouter(prefix="/admin/usuarios", tags=["Usuarios"])


def get_usuario_service(session: Session = Depends(get_session)) -> UsuarioService:
    """Construye UsuarioService usando el bind transaccional de la sesión inyectada."""
    bind = session.get_bind()
    return UsuarioService(
        UsuarioUnitOfWork(lambda: Session(bind, expire_on_commit=False))
    )


get_usuarios_service = get_usuario_service


@router.get(
    "",
    response_model=list[UserPublic],
    status_code=status.HTTP_200_OK,
    summary="Listar todos los usuarios",
)
def listar_usuarios(
    _current_user: Annotated[Usuario, Depends(require_role(["admin"]))],
    service: Annotated[UsuarioService, Depends(get_usuario_service)],
) -> list[UserPublic]:
    """Lista todas las cuentas del sistema (activas y desactivadas) para administración."""
    return service.list_usuarios()


@router.post(
    "/{id}/activar",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
    summary="Activar cuenta de usuario",
)
def activar_usuario(
    id: int,
    _current_user: Annotated[Usuario, Depends(require_role(["admin"]))],
    service: Annotated[UsuarioService, Depends(get_usuario_service)],
) -> UserPublic:
    """Realiza el alta lógica (``disabled=False``) de un usuario de forma idempotente."""
    try:
        return service.activar_usuario(id)
    except UsuarioNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{id}/desactivar",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
    summary="Desactivar cuenta de usuario",
)
def desactivar_usuario(
    id: int,
    current_user: Annotated[Usuario, Depends(require_role(["admin"]))],
    service: Annotated[UsuarioService, Depends(get_usuario_service)],
) -> UserPublic:
    """Realiza la baja lógica (``disabled=True``) impidiendo la auto-desactivación."""
    try:
        return service.desactivar_usuario(id, current_user_id=current_user.id)
    except AutoDesactivacionNoPermitida as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except UsuarioNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


__all__ = [
    "activar_usuario",
    "desactivar_usuario",
    "get_usuario_service",
    "get_usuarios_service",
    "listar_usuarios",
    "router",
]
