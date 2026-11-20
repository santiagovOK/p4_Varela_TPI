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
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    hash_password,
    pwd_context,
    verify_password,
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
    "create_access_token",
    "create_all_tables",
    "create_db_and_tables",
    "decode_access_token",
    "engine",
    "get_password_hash",
    "get_session",
    "get_settings",
    "hash_password",
    "pwd_context",
    "session_factory",
    "settings",
    "verify_password",
]
