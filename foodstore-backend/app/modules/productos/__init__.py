"""Módulo de gestión de productos del catálogo."""

from app.modules.productos.models import Producto
from app.modules.productos.repository import ProductoRepository
from app.modules.productos.router import get_producto_service, router
from app.modules.productos.schemas import (
    ProductoCreate,
    ProductoRead,
    ProductoStockUpdate,
    ProductoUpdate,
    ProductosPaginados,
)
from app.modules.productos.service import (
    CategoriaNoEncontrada,
    DatosProductoInvalidos,
    ProductoNoEncontrado,
    ProductoService,
)
from app.modules.productos.unit_of_work import ProductoUnitOfWork

__all__ = [
    "CategoriaNoEncontrada",
    "DatosProductoInvalidos",
    "Producto",
    "ProductoCreate",
    "ProductoNoEncontrado",
    "ProductoRead",
    "ProductoRepository",
    "ProductoService",
    "ProductoStockUpdate",
    "ProductoUnitOfWork",
    "ProductoUpdate",
    "ProductosPaginados",
    "get_producto_service",
    "router",
]
