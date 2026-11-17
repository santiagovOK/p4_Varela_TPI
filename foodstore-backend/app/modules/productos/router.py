"""Router HTTP para el módulo de Productos (base lista para migración TPI)."""

from fastapi import APIRouter

router = APIRouter(
    prefix="/api/v1/productos",
    tags=["Productos"],
)

__all__ = ["router"]
