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
from app.core.deps import (
    ACCESS_COOKIE_NAME,
    AdminUserDep,
    CurrentActiveUserDep,
    CurrentUserDep,
    OAuth2PasswordBearerWithCookie,
    get_current_active_user,
    get_current_user,
    oauth2_scheme,
    require_role,
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
    "ACCESS_COOKIE_NAME",
    "AdminUserDep",
    "BaseRepository",
    "CurrentActiveUserDep",
    "CurrentUserDep",
    "DATABASE_URL",
    "ModelType",
    "OAuth2PasswordBearerWithCookie",
    "SessionDep",
    "Settings",
    "UnitOfWork",
    "UnitOfWorkBase",
    "create_access_token",
    "create_all_tables",
    "create_db_and_tables",
    "decode_access_token",
    "engine",
    "get_current_active_user",
    "get_current_user",
    "get_password_hash",
    "get_session",
    "get_settings",
    "hash_password",
    "oauth2_scheme",
    "pwd_context",
    "require_role",
    "session_factory",
    "settings",
    "verify_password",
]
