"""Schemas SQLModel (DTOs) para el módulo de Categorías.

Consigna TPI (docs/consignas_tpi.md):
- Schemas de Categoria: `CategoriaCreate`, `CategoriaUpdate` (actualización parcial
  PUT con todos los campos opcionales `| None = None`) y `CategoriaRead`.
- Criterio 2: Modelo de datos.
- Criterio 5: API de catálogo.
"""

from sqlmodel import Field, SQLModel


class CategoriaCreate(SQLModel):
    """DTO de entrada para crear una categoría."""

    nombre: str = Field(min_length=2, max_length=100)
    descripcion: str | None = Field(default=None)


class CategoriaUpdate(SQLModel):
    """DTO de entrada para actualización parcial (PUT) de una categoría."""

    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    descripcion: str | None = Field(default=None)


class CategoriaRead(SQLModel):
    """DTO de salida pública para una categoría."""

    id: int
    nombre: str
    descripcion: str | None = None
    activo: bool


__all__ = ["CategoriaCreate", "CategoriaRead", "CategoriaUpdate"]
