"""Modelo de dominio SQLModel para Categorías del catálogo.

Consigna TPI (docs/consignas_tpi.pdf):
- Modelo de dominio Categoria: tabla `categorias` con `id`, `nombre` único
  (min_length=2, max_length=100, indexado), `descripcion` opcional y `activo`.
- Modelos y relaciones 1:N: relación `productos` (`back_populates="categoria"`).
- Criterio 2: Modelo de datos.
"""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.productos.models import Producto


class Categoria(SQLModel, table=True):
    """Entidad de dominio para categorías de productos del catálogo."""

    __tablename__ = "categorias"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(
        min_length=2,
        max_length=100,
        unique=True,
        index=True,
        nullable=False,
    )
    descripcion: str | None = Field(default=None, nullable=True)
    activo: bool = Field(default=True, nullable=False)

    # Relación 1:N con Producto (docs/consignas_tpi.pdf: Modelos y relaciones 1:N).
    productos: list["Producto"] = Relationship(back_populates="categoria")


__all__ = ["Categoria"]
