"""Router HTTP para el módulo de Categorías.

El prefijo global `/api/v1` se aplica al montar este router en `app/main.py`
(docs/consignas_tpi.md: app/main.py y API REST — Convenciones).
"""

from fastapi import APIRouter

router = APIRouter(
    prefix="/categorias",
    tags=["Categorías"],
)

__all__ = ["router"]
