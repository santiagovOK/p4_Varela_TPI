"""Módulo de gestión de categorías del catálogo."""

from app.modules.categorias.models import Categoria
from app.modules.categorias.router import router
from app.modules.categorias.schemas import (
    CategoriaCreate,
    CategoriaRead,
    CategoriaUpdate,
)

__all__ = [
    "Categoria",
    "CategoriaCreate",
    "CategoriaRead",
    "CategoriaUpdate",
    "router",
]
