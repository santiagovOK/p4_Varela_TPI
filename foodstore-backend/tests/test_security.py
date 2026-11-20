"""Pruebas unitarias de criptografía (bcrypt) y JWT en app/core/security.py."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core import (
    create_access_token as core_create_access_token,
    decode_access_token as core_decode_access_token,
    get_password_hash,
    hash_password as core_hash_password,
    verify_password as core_verify_password,
)
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_reexportaciones_en_app_core() -> None:
    assert core_hash_password is hash_password
    assert get_password_hash is hash_password
    assert core_verify_password is verify_password
    assert core_create_access_token is create_access_token
    assert core_decode_access_token is decode_access_token


def test_hash_y_verificacion_bcrypt() -> None:
    hashed_1 = hash_password("Admin1234!")
    hashed_2 = hash_password("Admin1234!")

    assert hashed_1 != "Admin1234!"
    assert hashed_1.startswith(("$2b$", "$2a$"))
    assert hashed_1 != hashed_2
    assert verify_password("Admin1234!", hashed_1) is True
    assert verify_password("Admin1234!", hashed_2) is True
    assert verify_password("Incorrecta1!", hashed_1) is False
    assert verify_password("", hashed_1) is False
    assert verify_password("Admin1234!", "hash_invalido_corrupto") is False


def test_limite_72_bytes_utf8_en_password() -> None:
    ascii_72 = "a" * 72
    multibyte_72 = "á" * 36  # 36 * 2 = 72 bytes UTF-8

    hash_ascii = hash_password(ascii_72)
    hash_utf8 = hash_password(multibyte_72)

    assert verify_password(ascii_72, hash_ascii) is True
    assert verify_password(multibyte_72, hash_utf8) is True

    with pytest.raises(ValueError, match="72 bytes"):
        hash_password("a" * 73)

    with pytest.raises(ValueError, match="72 bytes"):
        hash_password("á" * 37)  # 74 bytes UTF-8 aunque tenga 37 caracteres

    assert verify_password("a" * 73, hash_ascii) is False
    assert verify_password("á" * 37, hash_utf8) is False


def test_create_y_decode_access_token_con_settings() -> None:
    settings = get_settings()
    ahora = datetime.now(timezone.utc)

    token_dict = create_access_token({"sub": "admin", "role": "admin"})
    payload_dict = decode_access_token(token_dict)

    assert payload_dict is not None
    assert payload_dict["sub"] == "admin"
    assert payload_dict["role"] == "admin"
    assert payload_dict["type"] == "access"
    assert "exp" in payload_dict
    assert "hashed_password" not in payload_dict

    diff_seconds = payload_dict["exp"] - int(ahora.timestamp())
    expected_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert abs(diff_seconds - expected_seconds) <= 5

    token_str = create_access_token("cliente1", role="user")
    payload_str = decode_access_token(token_str)

    assert payload_str is not None
    assert payload_str["sub"] == "cliente1"
    assert payload_str["role"] == "user"
    assert payload_str["type"] == "access"


def test_decode_access_token_rechaza_tokens_invalidos() -> None:
    expirado = create_access_token(
        {"sub": "admin", "role": "admin"},
        expires_delta=timedelta(seconds=-5),
    )
    assert decode_access_token(expirado) is None

    otra_clave = create_access_token(
        {"sub": "admin", "role": "admin"},
        secret_key="otra_clave_secreta_muy_larga_para_pruebas_jwt",
    )
    assert decode_access_token(otra_clave) is None

    tipo_refresh = create_access_token(
        {"sub": "admin", "role": "admin", "type": "refresh"},
    )
    assert decode_access_token(tipo_refresh) is None

    assert decode_access_token("token.malformado.invalido") is None
    assert decode_access_token("") is None


def test_create_access_token_valida_claims_obligatorios() -> None:
    with pytest.raises(ValueError, match="sub"):
        create_access_token({"role": "admin"})

    with pytest.raises(ValueError, match="sub"):
        create_access_token({"sub": "   ", "role": "admin"})

    with pytest.raises(ValueError, match="role"):
        create_access_token({"sub": "admin", "role": "   "})
