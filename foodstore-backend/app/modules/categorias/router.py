"""Router HTTP para el módulo de Categorías (base lista para migración TPI)."""

from fastapi import APIRouter

router = APIRouter(
    prefix="/api/v1/categorias",
    tags=["Categorías"],
)

__all__ = ["router"]
