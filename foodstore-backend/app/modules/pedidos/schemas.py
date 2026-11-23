"""Schemas SQLModel (DTOs) para el módulo de Pedidos.

Consigna TPI (docs/consignas_tpi.pdf):
- Máquina de estados (`EstadoPedido`): `PENDIENTE`, `EN_PREPARACION`, `ENTREGADO`,
  `CANCELADO` (RN-02).
- RN-01: `PedidoCreate` requiere al menos un ítem (`items` con `min_length=1`).
- RN-05: `DetallePedidoRead` y `PedidoRead` exponen snapshots inmutables; no se definen
  schemas de edición (`PedidoUpdate`) ni borrado.
- RN-06: `FormaPago` (`EFECTIVO` o `TRANSFERENCIA`) y `direccion_entrega` (5–200).
- Schemas Pedido: `ItemPedidoCreate`, `PedidoCreate`, `DetallePedidoRead`,
  `PedidoRead`, `PedidosPaginados`, `CambioEstado` y `ResumenPedidos`.
- Criterio 2: Modelo de datos.
- Criterio 6: API de pedidos y reglas de negocio.
"""

from datetime import datetime
from typing import Literal

from sqlmodel import Field, SQLModel

EstadoPedido = Literal["PENDIENTE", "EN_PREPARACION", "ENTREGADO", "CANCELADO"]
FormaPago = Literal["EFECTIVO", "TRANSFERENCIA"]


class ItemPedidoCreate(SQLModel):
    """DTO de entrada para cada línea de producto al crear un pedido."""

    producto_id: int = Field(ge=1)
    cantidad: int = Field(ge=1)


class PedidoCreate(SQLModel):
    """DTO de entrada para crear un pedido (RN-01, RN-06)."""

    items: list[ItemPedidoCreate] = Field(min_length=1)
    forma_pago: FormaPago
    direccion_entrega: str = Field(min_length=5, max_length=200)
    notas: str | None = Field(default=None)


class DetallePedidoRead(SQLModel):
    """DTO de salida para una línea inmutable (snapshot) de pedido (RN-05)."""

    producto_id: int
    nombre_producto: str
    precio_unitario: float
    cantidad: int
    subtotal: float


class PedidoRead(SQLModel):
    """DTO de salida pública para un pedido con sus líneas de detalle."""

    id: int
    usuario_id: int
    estado: EstadoPedido
    forma_pago: FormaPago
    direccion_entrega: str
    notas: str | None = None
    total: float
    created_at: datetime
    updated_at: datetime
    items: list[DetallePedidoRead]


class PedidosPaginados(SQLModel):
    """DTO de salida paginada para listados de pedidos."""

    total: int
    items: list[PedidoRead]


class CambioEstado(SQLModel):
    """DTO de entrada para transición administrativa de estado de pedido (RN-02)."""

    estado: EstadoPedido


class ResumenPedidos(SQLModel):
    """DTO de salida para indicadores administrativos de pedidos."""

    pendientes: int
    en_preparacion: int
    entregados: int
    cancelados: int
    pedidos_hoy: int
    ingresos_entregados: float


__all__ = [
    "CambioEstado",
    "DetallePedidoRead",
    "EstadoPedido",
    "FormaPago",
    "ItemPedidoCreate",
    "PedidoCreate",
    "PedidoRead",
    "PedidosPaginados",
    "ResumenPedidos",
]
