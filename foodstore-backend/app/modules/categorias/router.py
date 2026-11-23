"""Router HTTP para el módulo de Categorías (`/api/v1/categorias/*`).

El prefijo global `/api/v1` se aplica al montar este router en `app/main.py`
(docs/consignas_tpi.pdf: app/main.py y API REST — Convenciones).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import require_role
from app.modules.categorias.schemas import CategoriaCreate, CategoriaRead, CategoriaUpdate
from app.modules.categorias.service import (
    CategoriaNoEncontrada,
    CategoriaService,
    DatosCategoriaInvalidos,
    NombreDuplicado,
)
from app.modules.categorias.unit_of_work import CategoriaUnitOfWork
from app.modules.usuarios.models import Usuario

router = APIRouter(
    prefix="/categorias",
    tags=["Categorías"],
)


def get_categoria_service(session: Session = Depends(get_session)) -> CategoriaService:
    """Construye ``CategoriaService`` usando el bind transaccional de la sesión."""
    bind = session.get_bind()
    return CategoriaService(
        CategoriaUnitOfWork(lambda: Session(bind, expire_on_commit=False))
    )


get_categorias_service = get_categoria_service


@router.get(
    "",
    response_model=list[CategoriaRead],
    status_code=status.HTTP_200_OK,
    summary="Listar categorías activas",
)
def listar_categorias(
    service: Annotated[CategoriaService, Depends(get_categoria_service)],
) -> list[CategoriaRead]:
    """Lista las categorías activas disponibles en el catálogo público."""
    return service.list_categorias()


@router.get(
    "/{id}",
    response_model=CategoriaRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener categoría por ID",
)
def obtener_categoria(
    id: int,
    service: Annotated[CategoriaService, Depends(get_categoria_service)],
) -> CategoriaRead:
    """Obtiene el detalle de una categoría activa por su identificador."""
    try:
        return service.get_categoria(id)
    except CategoriaNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=CategoriaRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear categoría",
)
def crear_categoria(
    data: CategoriaCreate,
    _current_user: Annotated[Usuario, Depends(require_role(["admin"]))],
    service: Annotated[CategoriaService, Depends(get_categoria_service)],
) -> CategoriaRead:
    """Crea una nueva categoría (solo administradores)."""
    try:
        return service.create_categoria(data)
    except NombreDuplicado as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except DatosCategoriaInvalidos as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put(
    "/{id}",
    response_model=CategoriaRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar categoría",
)
def actualizar_categoria(
    id: int,
    data: CategoriaUpdate,
    _current_user: Annotated[Usuario, Depends(require_role(["admin"]))],
    service: Annotated[CategoriaService, Depends(get_categoria_service)],
) -> CategoriaRead:
    """Actualiza parcialmente una categoría activa (solo administradores)."""
    try:
        return service.update_categoria(id, data)
    except CategoriaNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except NombreDuplicado as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except DatosCategoriaInvalidos as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dar de baja lógica una categoría",
)
def eliminar_categoria(
    id: int,
    _current_user: Annotated[Usuario, Depends(require_role(["admin"]))],
    service: Annotated[CategoriaService, Depends(get_categoria_service)],
) -> Response:
    """Realiza la baja lógica de una categoría activa (solo administradores)."""
    try:
        service.delete_categoria(id)
    except CategoriaNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["get_categoria_service", "get_categorias_service", "router"]
