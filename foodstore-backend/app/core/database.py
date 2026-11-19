"""Configuración del motor de base de datos, fábrica de sesiones y creación de tablas.

Consigna TPI (docs/consignas_tpi.md):
- Componentes del núcleo (app/core/database.py): engine, create_all_tables y
  session_factory consumiendo settings.DATABASE_URL desde app.core.config.
- Stack del backend: SQLModel sobre PostgreSQL (psycopg2-binary) con soporte
  de desarrollo/pruebas en SQLite.
- Regla del Unit of Work: sesiones creadas con expire_on_commit=False.
- Criterio 1: Backend: estructura y configuración.
- CE-05: Arranque autónomo con uvicorn app.main:app inicializando esquema vía
  create_all_tables() sin depender de setup.sh.
"""

from collections.abc import Generator
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[2]


def normalize_database_url(raw_url: str) -> str:
    """Normaliza la URL de conexión para PostgreSQL (psycopg2) y SQLite relativa."""
    url = raw_url.strip()
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if url.startswith("sqlite:///./"):
        relative_path = url.removeprefix("sqlite:///./")
        resolved_path = (BACKEND_DIR / relative_path).resolve()
        return f"sqlite:///{resolved_path}"
    return url


def _configurar_sqlite(dbapi_connection: Any, _connection_record: Any) -> None:
    """Registra char_length y activa PRAGMA foreign_keys=ON en conexiones SQLite."""
    if hasattr(dbapi_connection, "create_function"):
        dbapi_connection.create_function("char_length", 1, len)
    if hasattr(dbapi_connection, "cursor"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _build_engine(database_url: str) -> Engine:
    """Construye el motor SQLAlchemy/SQLModel para PostgreSQL o SQLite."""
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        is_in_memory = (
            ":memory:" in database_url or database_url.rstrip("/") == "sqlite:"
        )
        if is_in_memory:
            eng = create_engine(
                database_url,
                echo=False,
                connect_args=connect_args,
                poolclass=StaticPool,
            )
        else:
            eng = create_engine(
                database_url,
                echo=False,
                connect_args=connect_args,
                pool_pre_ping=True,
            )
        event.listens_for(eng, "connect")(_configurar_sqlite)
        return eng

    return create_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )


DATABASE_URL: str = normalize_database_url(settings.DATABASE_URL)

engine: Engine = _build_engine(DATABASE_URL)


def session_factory() -> Session:
    """Crea una nueva sesión SQLModel con expire_on_commit=False (regla Unit of Work)."""
    return Session(engine, expire_on_commit=False)


def create_all_tables(target_engine: Engine | None = None) -> None:
    """Crea todas las tablas registradas en los metadatos de SQLModel."""
    # Registra los modelos de dominio antes de generar el esquema DDL.
    from app.modules.categorias.models import Categoria  # noqa: F401
    from app.modules.pedidos.models import DetallePedido, Pedido  # noqa: F401
    from app.modules.productos.models import Producto  # noqa: F401
    from app.modules.usuarios.models import Usuario  # noqa: F401

    SQLModel.metadata.create_all(target_engine or engine)


def create_db_and_tables() -> None:
    """Alias compatible de create_all_tables()."""
    create_all_tables()


def get_session() -> Generator[Session, None, None]:
    """Provee una sesión SQLModel por solicitud HTTP y garantiza su cierre."""
    with session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

__all__ = [
    "BACKEND_DIR",
    "DATABASE_URL",
    "SessionDep",
    "create_all_tables",
    "create_db_and_tables",
    "engine",
    "get_session",
    "normalize_database_url",
    "session_factory",
]
