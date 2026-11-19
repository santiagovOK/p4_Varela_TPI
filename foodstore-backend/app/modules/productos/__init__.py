"""Módulo de gestión de productos del catálogo."""

from app.modules.productos.models import Producto
from app.modules.productos.router import router
from app.modules.productos.schemas import (
    ProductoCreate,
    ProductoRead,
    ProductoStockUpdate,
    ProductoUpdate,
    ProductosPaginados,
)

__all__ = [
    "Producto",
    "ProductoCreate",
    "ProductoRead",
    "ProductoStockUpdate",
    "ProductoUpdate",
    "ProductosPaginados",
    "router",
]
