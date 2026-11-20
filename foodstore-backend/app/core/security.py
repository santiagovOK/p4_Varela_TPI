"""Utilidades de criptografía (bcrypt) y tokens JWT para Food Store."""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from app.core.config import get_settings

MAX_BCRYPT_PASSWORD_BYTES = 72
ACCESS_TOKEN_TYPE = "access"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _validate_password_bytes(password: str) -> str:
    """Valida que la contraseña sea un string no vacío y no supere 72 bytes UTF-8."""
    if not isinstance(password, str) or not password:
        raise ValueError("La contraseña no puede estar vacía.")
    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError("La contraseña no puede superar los 72 bytes en UTF-8.")
    return password


def hash_password(password: str) -> str:
    """Genera un hash bcrypt seguro validando el límite de 72 bytes UTF-8."""
    validated = _validate_password_bytes(password)
    return pwd_context.hash(validated)


get_password_hash = hash_password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña plana contra su hash bcrypt sin propagar errores."""
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False
    if not plain_password or not hashed_password:
        return False
    if len(plain_password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError, UnknownHashError):
        return False


def create_access_token(
    data: dict[str, Any] | str,
    *,
    role: str = "user",
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
    algorithm: str | None = None,
) -> str:
    """Crea y firma un JWT de acceso con claims obligatorios sub, role, type y exp."""
    if isinstance(data, str):
        to_encode: dict[str, Any] = {"sub": data, "role": role}
    elif isinstance(data, dict):
        to_encode = dict(data)
        if to_encode.get("role") is None:
            to_encode["role"] = role
    else:
        raise ValueError("El argumento 'data' debe ser un diccionario o un string 'sub'.")

    sub = to_encode.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise ValueError("El claim 'sub' es obligatorio para generar el token de acceso.")
    to_encode["sub"] = sub.strip()

    resolved_role = to_encode.get("role")
    if not isinstance(resolved_role, str) or not resolved_role.strip():
        raise ValueError("El claim 'role' es obligatorio para generar el token de acceso.")
    to_encode["role"] = resolved_role.strip()

    to_encode.setdefault("type", ACCESS_TOKEN_TYPE)

    current_settings = get_settings() if (
        expires_delta is None or secret_key is None or algorithm is None
    ) else None

    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        assert current_settings is not None
        expire = now + timedelta(minutes=current_settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.setdefault("iat", now)
    to_encode["exp"] = expire

    key = secret_key if secret_key is not None else current_settings.SECRET_KEY  # type: ignore[union-attr]
    if not isinstance(key, str) or not key.strip():
        raise ValueError("SECRET_KEY no puede estar vacía.")

    algo = algorithm if algorithm is not None else current_settings.ALGORITHM  # type: ignore[union-attr]
    if not isinstance(algo, str) or not algo.strip():
        raise ValueError("ALGORITHM no puede estar vacío.")

    return jwt.encode(to_encode, key, algorithm=algo)


def decode_access_token(
    token: str,
    *,
    secret_key: str | None = None,
    algorithm: str | None = None,
) -> dict[str, Any] | None:
    """Decodifica y valida un JWT de acceso; retorna None si es inválido o expiró."""
    if not token or not isinstance(token, str):
        return None

    current_settings = get_settings() if (secret_key is None or algorithm is None) else None

    key = secret_key if secret_key is not None else current_settings.SECRET_KEY  # type: ignore[union-attr]
    if not isinstance(key, str) or not key.strip():
        raise ValueError("SECRET_KEY no puede estar vacía.")

    algo = algorithm if algorithm is not None else current_settings.ALGORITHM  # type: ignore[union-attr]
    if not isinstance(algo, str) or not algo.strip():
        raise ValueError("ALGORITHM no puede estar vacío.")

    try:
        payload = jwt.decode(token, key, algorithms=[algo])
    except JWTError:
        return None

    if not isinstance(payload, dict):
        return None

    sub = payload.get("sub")
    token_type = payload.get("type")
    role = payload.get("role")
    exp = payload.get("exp")

    if not isinstance(sub, str) or not sub.strip():
        return None
    if token_type != ACCESS_TOKEN_TYPE:
        return None
    if not isinstance(role, str) or not role.strip():
        return None
    if exp is None:
        return None

    return payload
