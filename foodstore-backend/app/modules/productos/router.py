"""Router HTTP para el módulo de Productos (`/api/v1/productos/*`).

El prefijo global `/api/v1` se aplica al montar este router en `app/main.py`
(docs/consignas_tpi.md: app/main.py y API REST — Convenciones).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import require_role
from app.modules.productos.schemas import (
    ProductoCreate,
    ProductoRead,
    ProductoStockUpdate,
    ProductoUpdate,
    ProductosPaginados,
)
from app.modules.productos.service import (
    CategoriaNoEncontrada,
    DatosProductoInvalidos,
    ProductoNoEncontrado,
    ProductoService,
)
from app.modules.productos.unit_of_work import ProductoUnitOfWork
from app.modules.usuarios.models import Usuario

router = APIRouter(
    prefix="/productos",
    tags=["Productos"],
)


def get_producto_service(session: Session = Depends(get_session)) -> ProductoService:
    """Construye ``ProductoService`` usando el bind transaccional de la sesión."""
    bind = session.get_bind()
    return ProductoService(
        ProductoUnitOfWork(lambda: Session(bind, expire_on_commit=False))
    )


get_productos_service = get_producto_service


@router.get(
    "",
    response_model=ProductosPaginados,
    status_code=status.HTTP_200_OK,
    summary="Listar productos activos paginados",
)
def listar_productos(
    service: Annotated[ProductoService, Depends(get_producto_service)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query()] = None,
    categoria_id: Annotated[int | None, Query(ge=1)] = None,
    disponible: Annotated[bool | None, Query()] = None,
) -> ProductosPaginados:
    """Lista productos activos con paginación y filtros de búsqueda."""
    return service.list_productos(
        skip=skip,
        limit=limit,
        search=search,
        categoria_id=categoria_id,
        disponible=disponible,
    )


@router.get(
    "/{id}",
    response_model=ProductoRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener producto por ID",
)
def obtener_producto(
    id: int,
    service: Annotated[ProductoService, Depends(get_producto_service)],
) -> ProductoRead:
    """Obtiene el detalle de un producto activo con su categoría asociada."""
    try:
        return service.get_producto(id)
    except ProductoNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=ProductoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear producto",
)
def crear_producto(
    data: ProductoCreate,
    _current_user: Annotated[Usuario, Depends(require_role(["admin"]))],
    service: Annotated[ProductoService, Depends(get_producto_service)],
) -> ProductoRead:
    """Crea un nuevo producto en el catálogo (solo administradores)."""
    try:
        return service.create_producto(data)
    except CategoriaNoEncontrada as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DatosProductoInvalidos as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put(
    "/{id}",
    response_model=ProductoRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar producto",
)
def actualizar_producto(
    id: int,
    data: ProductoUpdate,
    _current_user: Annotated[Usuario, Depends(require_role(["admin"]))],
    service: Annotated[ProductoService, Depends(get_producto_service)],
) -> ProductoRead:
    """Actualiza parcialmente un producto activo (solo administradores)."""
    try:
        return service.update_producto(id, data)
    except (ProductoNoEncontrado, CategoriaNoEncontrada) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DatosProductoInvalidos as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{id}/stock",
    response_model=ProductoRead,
    status_code=status.HTTP_200_OK,
    summary="Actualizar stock y disponibilidad de un producto",
)
def actualizar_stock_producto(
    id: int,
    data: ProductoStockUpdate,
    _current_user: Annotated[Usuario, Depends(require_role(["admin"]))],
    service: Annotated[ProductoService, Depends(get_producto_service)],
) -> ProductoRead:
    """Actualiza stock y disponibilidad de un producto activo (solo administradores)."""
    try:
        return service.update_stock(id, data)
    except ProductoNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DatosProductoInvalidos as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dar de baja lógica un producto",
)
def eliminar_producto(
    id: int,
    _current_user: Annotated[Usuario, Depends(require_role(["admin"]))],
    service: Annotated[ProductoService, Depends(get_producto_service)],
) -> Response:
    """Da de baja lógica un producto activo marcando ``activo = False`` (solo administradores)."""
    try:
        service.delete_producto(id)
    except ProductoNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["get_producto_service", "get_productos_service", "router"]
