"""Modelo de dominio SQLModel para Productos del catálogo.

Consigna TPI (docs/consignas_tpi.pdf):
- Modelo de dominio Producto: tabla `productos` con `id`, `categoria_id` (FK a
  `categorias.id`), `nombre`, `descripcion`, `precio_base` (>= 0), `imagen_url`,
  `stock` (entero >= 0), `disponible` y `activo`.
- Modelos y relaciones 1:N: relación `categoria` (`back_populates="productos"`) y
  `detalles` (`back_populates="producto"`).
- Criterio 2: Modelo de datos.
"""

from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.categorias.models import Categoria
    from app.modules.pedidos.models import DetallePedido


class Producto(SQLModel, table=True):
    """Entidad de dominio para productos del catálogo."""

    __tablename__ = "productos"

    id: int | None = Field(default=None, primary_key=True)
    categoria_id: int = Field(
        foreign_key="categorias.id",
        nullable=False,
        index=True,
    )
    nombre: str = Field(min_length=1, nullable=False, index=True)
    descripcion: str | None = Field(default=None, nullable=True)
    precio_base: float = Field(ge=0, nullable=False)
    imagen_url: str | None = Field(default=None, nullable=True)
    stock: int = Field(default=0, ge=0, nullable=False)
    disponible: bool = Field(default=True, nullable=False)
    activo: bool = Field(default=True, nullable=False)

    # Relación N:1 con Categoria (docs/consignas_tpi.pdf: Modelos y relaciones 1:N).
    categoria: Optional["Categoria"] = Relationship(back_populates="productos")
    # Relación 1:N con DetallePedido (docs/consignas_tpi.pdf: Producto.detalles).
    detalles: list["DetallePedido"] = Relationship(back_populates="producto")


__all__ = ["Producto"]
