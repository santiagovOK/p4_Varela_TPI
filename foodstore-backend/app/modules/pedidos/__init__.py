"""Módulo de gestión de pedidos y detalles de pedido."""

from app.modules.pedidos.models import DetallePedido, Pedido
from app.modules.pedidos.repository import PedidoRepository
from app.modules.pedidos.router import (
    get_pedido_service,
    get_pedidos_service,
    router,
)
from app.modules.pedidos.schemas import (
    CambioEstado,
    DetallePedidoRead,
    EstadoPedido,
    FormaPago,
    ItemPedidoCreate,
    PedidoCreate,
    PedidoRead,
    PedidosPaginados,
    ResumenPedidos,
)
from app.modules.pedidos.service import (
    TRANSICIONES_VALIDAS,
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

__all__ = [
    "TRANSICIONES_VALIDAS",
    "CambioEstado",
    "DatosPedidoInvalidos",
    "DetallePedido",
    "DetallePedidoRead",
    "EstadoPedido",
    "FormaPago",
    "ItemPedidoCreate",
    "Pedido",
    "PedidoAjeno",
    "PedidoCreate",
    "PedidoNoEncontrado",
    "PedidoRead",
    "PedidoRepository",
    "PedidoService",
    "PedidoUnitOfWork",
    "PedidosPaginados",
    "ProductoNoDisponible",
    "ProductoNoEncontrado",
    "ProductoRepetido",
    "ResumenPedidos",
    "StockInsuficiente",
    "TransicionInvalida",
    "get_pedido_service",
    "get_pedidos_service",
    "router",
]
