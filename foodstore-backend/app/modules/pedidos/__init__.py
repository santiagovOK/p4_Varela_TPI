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
    DatosPedidoInvalidos,
    PedidoService,
    ProductoNoDisponible,
    ProductoNoEncontrado,
    ProductoRepetido,
    StockInsuficiente,
)
from app.modules.pedidos.unit_of_work import PedidoUnitOfWork

__all__ = [
    "CambioEstado",
    "DatosPedidoInvalidos",
    "DetallePedido",
    "DetallePedidoRead",
    "EstadoPedido",
    "FormaPago",
    "ItemPedidoCreate",
    "Pedido",
    "PedidoCreate",
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
    "get_pedido_service",
    "get_pedidos_service",
    "router",
]
