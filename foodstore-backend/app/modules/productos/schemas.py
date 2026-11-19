"""Schemas SQLModel (DTOs) para el módulo de Productos.

Consigna TPI (docs/consignas_tpi.md):
- Schemas Producto: `ProductoCreate`, `ProductoUpdate` (actualización parcial),
  `ProductoRead` (con `categoria: CategoriaRead`), `ProductoStockUpdate` y
  `ProductosPaginados` (`{total, items}`).
- API REST Productos: respuestas paginadas y actualización de stock/disponibilidad.
- Criterio 2: Modelo de datos.
- Criterio 5: API de catálogo.
"""

from sqlmodel import Field, SQLModel

from app.modules.categorias.schemas import CategoriaRead


class ProductoCreate(SQLModel):
    """DTO de entrada para crear un producto."""

    nombre: str = Field(min_length=1)
    descripcion: str | None = Field(default=None)
    precio_base: float = Field(ge=0)
    imagen_url: str | None = Field(default=None)
    stock: int = Field(default=0, ge=0)
    disponible: bool = Field(default=True)
    categoria_id: int = Field(ge=1)


class ProductoUpdate(SQLModel):
    """DTO de entrada para actualización parcial de un producto."""

    nombre: str | None = Field(default=None, min_length=1)
    descripcion: str | None = Field(default=None)
    precio_base: float | None = Field(default=None, ge=0)
    imagen_url: str | None = Field(default=None)
    stock: int | None = Field(default=None, ge=0)
    disponible: bool | None = Field(default=None)
    categoria_id: int | None = Field(default=None, ge=1)


class ProductoRead(SQLModel):
    """DTO de salida pública para un producto con su categoría asociada."""

    id: int
    nombre: str
    descripcion: str | None = None
    precio_base: float
    imagen_url: str | None = None
    stock: int
    disponible: bool
    categoria_id: int
    activo: bool
    categoria: CategoriaRead


class ProductoStockUpdate(SQLModel):
    """DTO de entrada para actualizar stock y disponibilidad de un producto (PATCH)."""

    stock: int = Field(ge=0)
    disponible: bool


class ProductosPaginados(SQLModel):
    """DTO de salida paginada para listados de productos."""

    total: int
    items: list[ProductoRead]


__all__ = [
    "ProductoCreate",
    "ProductoRead",
    "ProductoStockUpdate",
    "ProductoUpdate",
    "ProductosPaginados",
]
