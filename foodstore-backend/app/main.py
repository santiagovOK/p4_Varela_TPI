"""Punto de entrada principal de la aplicación FastAPI Food Store."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import create_db_and_tables
from app.modules.categorias.router import router as categorias_router
from app.modules.productos.router import router as productos_router

# Orígenes permitidos para el frontend (Vite dev server en localhost y 127.0.0.1)
_env_frontend = os.getenv("FRONTEND_ORIGIN", "").strip()
CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
if _env_frontend and _env_frontend not in CORS_ORIGINS:
    CORS_ORIGINS.append(_env_frontend)

OPENAPI_TAGS: list[dict[str, str]] = [
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
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gestiona el ciclo de vida de la aplicación: crea tablas al iniciar."""
    create_db_and_tables()
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

app.include_router(categorias_router)
app.include_router(productos_router)


__all__ = ["CORS_ORIGINS", "OPENAPI_TAGS", "app", "lifespan"]
