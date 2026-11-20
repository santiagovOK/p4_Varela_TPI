"""Router HTTP para el módulo de Pedidos (`/api/v1/pedidos/*`).

El prefijo global `/api/v1` se aplica al montar este router en `app/main.py`
(docs/consignas_tpi.md: app/main.py y API REST — Convenciones).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.core.database import get_session
from app.core.deps import get_current_active_user
from app.modules.pedidos.schemas import PedidoCreate, PedidoRead
from app.modules.pedidos.service import (
    DatosPedidoInvalidos,
    PedidoService,
    ProductoNoDisponible,
    ProductoNoEncontrado,
    ProductoRepetido,
    StockInsuficiente,
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


__all__ = ["get_pedido_service", "get_pedidos_service", "router"]
