"""Modelos de dominio SQLModel para Pedidos y Detalle de Pedidos.

Consigna TPI (docs/consignas_tpi.pdf):
- Entidades Pedido y DetallePedido: tablas `pedidos` y `detalle_pedidos` con
  relaciones UML `Usuario.pedidos`/`Pedido.usuario`, `Pedido.items`/`DetallePedido.pedido`
  y `Producto.detalles`/`DetallePedido.producto`.
- Máquina de estados: `PENDIENTE` (inicial), `EN_PREPARACION`, `ENTREGADO`, `CANCELADO`.
- RN-01: Creación transaccional con descuento de stock y snapshot de nombre/precio.
- RN-02: Transiciones de estado válidas.
- RN-05: Inmutabilidad de líneas (`nombre_producto`, `precio_unitario`, `subtotal`) y
  `total` tras la creación; sin edición ni borrado de pedidos.
- RN-06: `forma_pago` (`EFECTIVO` o `TRANSFERENCIA`) y `direccion_entrega` (5–200).
- Criterio 2: Modelo de datos.
- Criterio 6: API de pedidos y reglas de negocio.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.productos.models import Producto
    from app.modules.usuarios.models import Usuario


class Pedido(SQLModel, table=True):
    """Entidad de dominio para pedidos realizados por clientes."""

    __tablename__ = "pedidos"

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(
        foreign_key="usuarios.id",
        nullable=False,
        index=True,
    )
    estado: str = Field(default="PENDIENTE", nullable=False, index=True)
    forma_pago: str = Field(nullable=False)
    direccion_entrega: str = Field(min_length=5, max_length=200, nullable=False)
    notas: str | None = Field(default=None, nullable=True)
    total: float = Field(default=0.0, ge=0, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relaciones UML (docs/consignas_tpi.pdf: Pedido.usuario y Pedido.items).
    usuario: Optional["Usuario"] = Relationship(back_populates="pedidos")
    items: list["DetallePedido"] = Relationship(
        back_populates="pedido",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class DetallePedido(SQLModel, table=True):
    """Entidad de dominio para líneas inmutables (snapshots) de un pedido."""

    __tablename__ = "detalle_pedidos"

    id: int | None = Field(default=None, primary_key=True)
    pedido_id: int = Field(
        foreign_key="pedidos.id",
        nullable=False,
        index=True,
    )
    producto_id: int = Field(
        foreign_key="productos.id",
        nullable=False,
        index=True,
    )
    cantidad: int = Field(ge=1, nullable=False)
    # Snapshot inmutable de nombre, precio unitario y subtotal (RN-01, RN-05).
    nombre_producto: str = Field(min_length=1, nullable=False)
    precio_unitario: float = Field(ge=0, nullable=False)
    subtotal: float = Field(ge=0, nullable=False)

    # Relaciones UML (docs/consignas_tpi.pdf: DetallePedido.pedido y DetallePedido.producto).
    pedido: Optional["Pedido"] = Relationship(back_populates="items")
    producto: Optional["Producto"] = Relationship(back_populates="detalles")


__all__ = ["DetallePedido", "Pedido"]
