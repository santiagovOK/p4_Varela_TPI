"""Punto de entrada principal de la aplicación FastAPI Food Store.

Consigna TPI (docs/consignas_tpi.md):
- app/main.py: crea la aplicación FastAPI, registra CORSMiddleware con
  allow_credentials=True y allow_origins=[settings.FRONTEND_ORIGIN] (nunca '*'),
  ejecuta create_all_tables() en lifespan y expone /docs y /redoc.
- API REST /api/v1: todos los routers del sistema se montan bajo API_V1_PREFIX.
- Criterio 1: Backend: estructura y configuración.
- CE-05: Arranque autónomo con uvicorn app.main:app sin depender de setup.sh.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_all_tables
from app.modules.auth.router import router as auth_router
from app.modules.categorias.router import router as categorias_router
from app.modules.productos.router import router as productos_router
from app.modules.usuarios.router import router as usuarios_router

API_V1_PREFIX = "/api/v1"
CORS_ORIGINS: list[str] = [settings.FRONTEND_ORIGIN]

OPENAPI_TAGS: list[dict[str, str]] = [
    {
        "name": "Health",
        "description": "Estado de disponibilidad de la API Food Store.",
    },
    {
        "name": "Autenticación",
        "description": "Registro público, login con cookie HttpOnly, logout y perfil de sesión.",
    },
    {
        "name": "Usuarios",
        "description": "Gestión administrativa de usuarios (listado, activación y desactivación).",
    },
    {
        "name": "Categorías",
        "description": "Operaciones sobre categorías de productos del catálogo.",
    },
    {
        "name": "Productos",
        "description": "Operaciones sobre productos, precios y stock del catálogo.",
    },
]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Inicializa el esquema de base de datos al arrancar."""
    create_all_tables()
    yield


app = FastAPI(
    title="Food Store — Sistema de pedidos de comida API",
    description="API REST modular para el catálogo y sistema de pedidos de Food Store.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(f"{API_V1_PREFIX}/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Verifica que la API está operativa."""
    return {"status": "ok"}


app.include_router(auth_router, prefix=API_V1_PREFIX)
app.include_router(usuarios_router, prefix=API_V1_PREFIX)
app.include_router(categorias_router, prefix=API_V1_PREFIX)
app.include_router(productos_router, prefix=API_V1_PREFIX)

__all__ = ["API_V1_PREFIX", "CORS_ORIGINS", "OPENAPI_TAGS", "app", "health_check", "lifespan"]
