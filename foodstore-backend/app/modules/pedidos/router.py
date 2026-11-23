"""Router HTTP para el módulo de Pedidos (`/api/v1/pedidos/*`).

El prefijo global `/api/v1` se aplica al montar este router en `app/main.py`
(docs/consignas_tpi.pdf: app/main.py y API REST — Convenciones).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user, require_role
from app.modules.pedidos.schemas import (
    CambioEstado,
    EstadoPedido,
    PedidoCreate,
    PedidoRead,
    PedidosPaginados,
    ResumenPedidos,
)
from app.modules.pedidos.service import (
    DatosPedidoInvalidos,
    PedidoAjeno,
    PedidoNoEncontrado,
    PedidoService,
    ProductoNoDisponible,
    ProductoNoEncontrado,
    ProductoRepetido,
    StockInsuficiente,
    TransicionInvalida,
)
from app.modules.pedidos.unit_of_work import PedidoUnitOfWork
from app.modules.usuarios.models import Usuario

router = APIRouter(
    prefix="/pedidos",
    tags=["Pedidos"],
)


def get_pedido_service(session: Session = Depends(get_session)) -> PedidoService:
    """Construye ``PedidoService`` usando el bind transaccional de la sesión."""
    bind = session.get_bind()
    return PedidoService(
        PedidoUnitOfWork(lambda: Session(bind, expire_on_commit=False))
    )


get_pedidos_service = get_pedido_service


@router.post(
    "",
    response_model=PedidoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pedido transaccional desde el carrito",
)
def crear_pedido(
    data: PedidoCreate,
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
    service: Annotated[PedidoService, Depends(get_pedido_service)],
) -> PedidoRead:
    """Crea un pedido atómico para el usuario autenticado activo."""
    assert current_user.id is not None
    try:
        return service.create_pedido(current_user.id, data)
    except ProductoNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (
        ProductoRepetido,
        ProductoNoDisponible,
        StockInsuficiente,
        DatosPedidoInvalidos,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=PedidosPaginados,
    status_code=status.HTTP_200_OK,
    summary="Listar pedidos paginados según rol (propios o todos)",
)
def listar_pedidos(
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
    service: Annotated[PedidoService, Depends(get_pedido_service)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    estado: Annotated[EstadoPedido | None, Query()] = None,
) -> PedidosPaginados:
    """Lista los pedidos del usuario autenticado o todos si es administrador."""
    assert current_user.id is not None
    return service.list_pedidos(
        usuario_id=current_user.id,
        role=current_user.role,
        skip=skip,
        limit=limit,
        estado=estado,
    )


@router.get(
    "/resumen",
    response_model=ResumenPedidos,
    status_code=status.HTTP_200_OK,
    summary="Obtener resumen administrativo de pedidos (admin)",
)
def obtener_resumen_pedidos(
    _admin_user: Annotated[Usuario, Depends(require_role(["admin"]))],
    service: Annotated[PedidoService, Depends(get_pedido_service)],
) -> ResumenPedidos:
    """Devuelve conteos por estado, pedidos del día e ingresos entregados."""
    return service.get_resumen()


@router.get(
    "/{id}",
    response_model=PedidoRead,
    status_code=status.HTTP_200_OK,
    summary="Obtener detalle de un pedido por ID",
)
def obtener_pedido(
    id: int,
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
    service: Annotated[PedidoService, Depends(get_pedido_service)],
) -> PedidoRead:
    """Devuelve el detalle de un pedido si el solicitante es su dueño o admin."""
    assert current_user.id is not None
    try:
        return service.get_pedido(
            id,
            usuario_id=current_user.id,
            role=current_user.role,
        )
    except PedidoNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PedidoAjeno as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{id}/estado",
    response_model=PedidoRead,
    status_code=status.HTTP_200_OK,
    summary="Avanzar o cancelar pedido según la máquina de estados (admin)",
)
def cambiar_estado_pedido(
    id: int,
    data: CambioEstado,
    _admin_user: Annotated[Usuario, Depends(require_role(["admin"]))],
    service: Annotated[PedidoService, Depends(get_pedido_service)],
) -> PedidoRead:
    """Cambia el estado de un pedido aplicando RN-02 y restitución de stock RN-03."""
    try:
        return service.cambiar_estado(id, data)
    except PedidoNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except TransicionInvalida as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{id}/cancelar",
    response_model=PedidoRead,
    status_code=status.HTTP_200_OK,
    summary="Cancelar pedido propio en estado PENDIENTE",
)
def cancelar_pedido(
    id: int,
    current_user: Annotated[Usuario, Depends(get_current_active_user)],
    service: Annotated[PedidoService, Depends(get_pedido_service)],
) -> PedidoRead:
    """Permite al dueño cancelar un pedido PENDIENTE restituyendo stock (RN-03, RN-04)."""
    assert current_user.id is not None
    try:
        return service.cancelar_pedido(id, usuario_id=current_user.id)
    except PedidoNoEncontrado as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PedidoAjeno as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except TransicionInvalida as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


__all__ = ["get_pedido_service", "get_pedidos_service", "router"]
