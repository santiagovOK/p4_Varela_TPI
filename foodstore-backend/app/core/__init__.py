"""Configuración transversal y motor de persistencia del backend Food Store."""

from app.core.base_repository import BaseRepository, ModelType
from app.core.config import Settings, get_settings, settings
from app.core.database import (
    DATABASE_URL,
    SessionDep,
    create_all_tables,
    create_db_and_tables,
    engine,
    get_session,
    session_factory,
)
from app.core.unit_of_work import UnitOfWork, UnitOfWorkBase

__all__ = [
    "BaseRepository",
    "DATABASE_URL",
    "ModelType",
    "SessionDep",
    "Settings",
    "UnitOfWork",
    "UnitOfWorkBase",
    "create_all_tables",
    "create_db_and_tables",
    "engine",
    "get_session",
    "get_settings",
    "session_factory",
    "settings",
]
