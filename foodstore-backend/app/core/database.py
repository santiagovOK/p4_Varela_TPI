"""Configuración del motor PostgreSQL (con soporte de fallback SQLite) y dependencia de sesión SQLModel."""

import os
from collections.abc import Generator
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import Depends
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

load_dotenv()

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg2://postgres:postgres@localhost:5432/foodstore"
)


def _resolve_database_url() -> str:
    """Obtiene y normaliza la cadena de conexión a la base de datos desde el entorno."""
    raw_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip()
    if not raw_url:
        return DEFAULT_DATABASE_URL
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return raw_url


def _configurar_sqlite(dbapi_connection: Any, _connection_record: Any) -> None:
    """Registra char_length y activa claves foráneas en conexiones SQLite de desarrollo/pruebas."""
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
        if ":memory:" in database_url:
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


DATABASE_URL: str = _resolve_database_url()

engine: Engine = _build_engine(DATABASE_URL)


def create_db_and_tables() -> None:
    """Crea todas las tablas registradas en los metadatos de SQLModel."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Provee una sesión transaccional de SQLModel por solicitud HTTP y garantiza su cierre."""
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

__all__ = [
    "DATABASE_URL",
    "SessionDep",
    "create_db_and_tables",
    "engine",
    "get_session",
]
