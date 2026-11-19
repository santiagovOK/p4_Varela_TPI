"""Pruebas unitarias de schemas SQLModel para Usuarios (E2.2)."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

import app.modules.usuarios as usuarios_pkg
from app.modules.usuarios import UserCreate, UserPublic, Usuario


def test_user_create_valido_y_restricciones_password_utf8() -> None:
    """Valida longitudes de campos, EmailStr y límite de 72 bytes UTF-8 en password."""
    u = UserCreate(
        username="jdoe",
        full_name="Juan Doe",
        email="jdoe@example.com",
        password="Password123!",
    )
    assert u.username == "jdoe"
    assert u.email == "jdoe@example.com"

    # Exactamente 72 bytes ASCII es válido.
    u_max = UserCreate(
        username="maxpass",
        full_name="Max Pass",
        email="max@example.com",
        password="a" * 72,
    )
    assert len(u_max.password) == 72

    # Menor a 8 caracteres -> error.
    with pytest.raises(ValidationError):
        UserCreate(
            username="short",
            full_name="Short Pass",
            email="short@example.com",
            password="1234567",
        )

    # Mayor a 72 caracteres -> error.
    with pytest.raises(ValidationError):
        UserCreate(
            username="long",
            full_name="Long Pass",
            email="long@example.com",
            password="a" * 73,
        )

    # <= 72 caracteres pero > 72 bytes en UTF-8 (ej. 37 caracteres de 2 bytes = 74 bytes).
    with pytest.raises(ValidationError):
        UserCreate(
            username="multibyte",
            full_name="Multi Byte",
            email="multi@example.com",
            password="á" * 37,
        )

    # Email inválido -> error.
    with pytest.raises(ValidationError):
        UserCreate(
            username="bademail",
            full_name="Bad Email",
            email="no-es-un-email",
            password="Password123!",
        )


def test_user_public_unificado_sin_hashed_password_ni_user_admin_public() -> None:
    """Valida los 7 campos exactos de UserPublic y ausencia de UserAdminPublic."""
    now = datetime.now(timezone.utc)
    usuario = Usuario(
        id=1,
        username="admin",
        full_name="Administrador",
        email="admin@example.com",
        hashed_password="secrethashvalue",
        role="admin",
        disabled=False,
        created_at=now,
    )

    dto = UserPublic.model_validate(usuario)
    assert set(UserPublic.model_fields.keys()) == {
        "id",
        "username",
        "full_name",
        "email",
        "role",
        "disabled",
        "created_at",
    }
    assert dto.id == 1
    assert dto.username == "admin"
    assert dto.role == "admin"
    assert dto.disabled is False
    assert dto.created_at == now
    assert "hashed_password" not in dto.model_dump()
    assert not hasattr(usuarios_pkg, "UserAdminPublic")
