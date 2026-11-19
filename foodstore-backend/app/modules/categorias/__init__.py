"""Módulo de gestión de categorías del catálogo."""

from app.modules.categorias.models import Categoria
from app.modules.categorias.repository import CategoriaRepository
from app.modules.categorias.router import router
from app.modules.categorias.schemas import (
    CategoriaCreate,
    CategoriaRead,
    CategoriaUpdate,
)
from app.modules.categorias.unit_of_work import CategoriaUnitOfWork

__all__ = [
    "Categoria",
    "CategoriaCreate",
    "CategoriaRead",
    "CategoriaRepository",
    "CategoriaUnitOfWork",
    "CategoriaUpdate",
    "router",
]
