"""Módulo de gestión de productos del catálogo."""

from app.modules.productos.models import Producto
from app.modules.productos.repository import ProductoRepository
from app.modules.productos.router import router
from app.modules.productos.schemas import (
    ProductoCreate,
    ProductoRead,
    ProductoStockUpdate,
    ProductoUpdate,
    ProductosPaginados,
)
from app.modules.productos.unit_of_work import ProductoUnitOfWork

__all__ = [
    "Producto",
    "ProductoCreate",
    "ProductoRead",
    "ProductoRepository",
    "ProductoStockUpdate",
    "ProductoUnitOfWork",
    "ProductoUpdate",
    "ProductosPaginados",
    "router",
]
