"""Pruebas de integración y unidad para el módulo de Autenticación (`/api/v1/auth/*`)."""

import importlib
from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.core.database import _build_engine, create_all_tables, get_session
from app.core.security import create_access_token, decode_access_token
from app.main import app
from app.modules.auth.router import ACCESS_COOKIE_NAME
from app.modules.usuarios.models import Usuario


@pytest.fixture
def auth_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, object]]:
    """Provee TestClient con base SQLite en memoria aislada por StaticPool."""
    test_engine = _build_engine("sqlite:///:memory:")
    create_all_tables(test_engine)
    monkeypatch.setattr("app.main.create_all_tables", lambda: create_all_tables(test_engine))

    def override_get_session() -> Iterator[Session]:
        with Session(test_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as client:
            yield client, test_engine
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()


def _register_sample_user(
    client: TestClient,
    *,
    username: str = "cliente1",
    full_name: str = "Cliente Uno",
    email: str = "cliente1@example.com",
    password: str = "ClaveSegura123!",
):
    return client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "full_name": full_name,
            "email": email,
            "password": password,
        },
    )


def test_register_crea_usuario_y_retorna_user_public_de_7_campos(
    auth_client: tuple[TestClient, object],
) -> None:
    """POST /register crea rol 'user', hashea con bcrypt y nunca expone password."""
    client, test_engine = auth_client
    resp = _register_sample_user(client)
    assert resp.status_code == 201
    data = resp.json()
    assert set(data.keys()) == {
        "id",
        "username",
        "full_name",
        "email",
        "role",
        "disabled",
        "created_at",
    }
    assert data["username"] == "cliente1"
    assert data["full_name"] == "Cliente Uno"
    assert data["email"] == "cliente1@example.com"
    assert data["role"] == "user"
    assert data["disabled"] is False
    assert "hashed_password" not in data
    assert "password" not in data

    with Session(test_engine, expire_on_commit=False) as session:
        user_db = session.exec(select(Usuario).where(Usuario.username == "cliente1")).first()
        assert user_db is not None
        assert user_db.hashed_password != "ClaveSegura123!"
        assert user_db.hashed_password.startswith("$2")


def test_register_duplicado_username_o_email_responde_409(
    auth_client: tuple[TestClient, object],
) -> None:
    """POST /register responde 409 Conflict si username o email ya existen."""
    client, _ = auth_client
    assert _register_sample_user(client).status_code == 201

    dup_username = _register_sample_user(
        client,
        username="cliente1",
        email="otro@example.com",
    )
    assert dup_username.status_code == 409

    dup_email = _register_sample_user(
        client,
        username="cliente2",
        email="cliente1@example.com",
    )
    assert dup_email.status_code == 409


def test_register_password_invalida_responde_422(
    auth_client: tuple[TestClient, object],
) -> None:
    """POST /register rechaza contraseñas menores a 8 chars o mayores a 72 bytes UTF-8."""
    client, _ = auth_client
    corta = _register_sample_user(client, username="u_corta", email="corta@example.com", password="1234567")
    assert corta.status_code == 422

    larga_utf8 = _register_sample_user(
        client,
        username="u_larga",
        email="larga@example.com",
        password="á" * 37,  # 74 bytes UTF-8
    )
    assert larga_utf8.status_code == 422


def test_login_token_emite_cookie_httponly_y_mensaje_sin_jwt(
    auth_client: tuple[TestClient, object],
) -> None:
    """POST /token devuelve {'message': 'Login exitoso'} y cookie HttpOnly con claims JWT."""
    client, _ = auth_client
    assert _register_sample_user(client).status_code == 201

    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "cliente1", "password": "ClaveSegura123!"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"message": "Login exitoso"}

    set_cookie = resp.headers.get("set-cookie", "")
    assert f"{ACCESS_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/" in set_cookie
    assert "SameSite=lax" in set_cookie.lower().replace("samesite=lax", "SameSite=lax") or "samesite=lax" in set_cookie.lower()
    assert "; secure" not in set_cookie.lower()

    cookie_token = client.cookies.get(ACCESS_COOKIE_NAME)
    assert cookie_token is not None
    payload = decode_access_token(cookie_token)
    assert payload is not None
    assert payload["sub"] == "cliente1"
    assert payload["role"] == "user"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_login_credenciales_invalidas_y_cuenta_desactivada(
    auth_client: tuple[TestClient, object],
) -> None:
    """POST /token responde 401 ante credenciales inválidas y 400 si disabled=True."""
    client, test_engine = auth_client
    assert _register_sample_user(client).status_code == 201

    bad_pass = client.post(
        "/api/v1/auth/token",
        data={"username": "cliente1", "password": "Incorrecta123!"},
    )
    assert bad_pass.status_code == 401

    unknown = client.post(
        "/api/v1/auth/token",
        data={"username": "no_existe", "password": "ClaveSegura123!"},
    )
    assert unknown.status_code == 401

    with Session(test_engine, expire_on_commit=False) as session:
        user_db = session.exec(select(Usuario).where(Usuario.username == "cliente1")).one()
        user_db.disabled = True
        session.add(user_db)
        session.commit()

    disabled_resp = client.post(
        "/api/v1/auth/token",
        data={"username": "cliente1", "password": "ClaveSegura123!"},
    )
    assert disabled_resp.status_code == 400
    assert disabled_resp.json()["detail"] == "Cuenta de usuario desactivada"


def test_cookie_secure_configurable_en_token_y_logout(
    auth_client: tuple[TestClient, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """COOKIE_SECURE / FRONTEND_ORIGIN HTTPS controlan el atributo Secure en login y logout."""
    client, _ = auth_client
    assert _register_sample_user(client).status_code == 201

    auth_router_module = importlib.import_module("app.modules.auth.router")
    base = get_settings()

    # 1) FRONTEND_ORIGIN HTTPS con COOKIE_SECURE=None -> Secure activo
    https_settings = Settings(
        DATABASE_URL=base.DATABASE_URL,
        SECRET_KEY=base.SECRET_KEY,
        ALGORITHM=base.ALGORITHM,
        ACCESS_TOKEN_EXPIRE_MINUTES=base.ACCESS_TOKEN_EXPIRE_MINUTES,
        FRONTEND_ORIGIN="https://foodstore.example.com",
        COOKIE_SECURE=None,
    )
    monkeypatch.setattr(auth_router_module, "get_settings", lambda: https_settings)

    login_https = client.post(
        "/api/v1/auth/token",
        data={"username": "cliente1", "password": "ClaveSegura123!"},
    )
    assert login_https.status_code == 200
    assert "secure" in login_https.headers.get("set-cookie", "").lower()

    logout_https = client.post("/api/v1/auth/logout")
    assert logout_https.status_code == 200
    assert "secure" in logout_https.headers.get("set-cookie", "").lower()

    # 2) COOKIE_SECURE=False explícito incluso con HTTPS -> Secure inactivo
    insecure_override = Settings(
        DATABASE_URL=base.DATABASE_URL,
        SECRET_KEY=base.SECRET_KEY,
        ALGORITHM=base.ALGORITHM,
        ACCESS_TOKEN_EXPIRE_MINUTES=base.ACCESS_TOKEN_EXPIRE_MINUTES,
        FRONTEND_ORIGIN="https://foodstore.example.com",
        COOKIE_SECURE=False,
    )
    monkeypatch.setattr(auth_router_module, "get_settings", lambda: insecure_override)

    login_no_secure = client.post(
        "/api/v1/auth/token",
        data={"username": "cliente1", "password": "ClaveSegura123!"},
    )
    assert login_no_secure.status_code == 200
    assert "; secure" not in login_no_secure.headers.get("set-cookie", "").lower()


def test_me_consulta_bd_con_cookie_y_rechaza_bearer_expirado_o_desactivado(
    auth_client: tuple[TestClient, object],
) -> None:
    """GET /me exige cookie válida, ignora Bearer y valida estado activo en BD."""
    client, test_engine = auth_client
    assert _register_sample_user(client).status_code == 201

    # Sin cookie -> 401
    assert client.get("/api/v1/auth/me").status_code == 401

    # Token válido enviado solo en Authorization: Bearer sin cookie -> 401
    bearer_token = create_access_token({"sub": "cliente1", "role": "user"})
    assert (
        client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {bearer_token}"},
        ).status_code
        == 401
    )

    # Token malformado en cookie -> 401
    client.cookies.set(ACCESS_COOKIE_NAME, "token.invalido.firma")
    assert client.get("/api/v1/auth/me").status_code == 401

    # Token expirado -> 401
    expired_token = create_access_token(
        {"sub": "cliente1", "role": "user"},
        expires_delta=timedelta(seconds=-10),
    )
    client.cookies.set(ACCESS_COOKIE_NAME, expired_token)
    assert client.get("/api/v1/auth/me").status_code == 401

    # Token con type != "access" -> 401
    wrong_type_token = create_access_token(
        {"sub": "cliente1", "role": "user", "type": "refresh"},
    )
    client.cookies.set(ACCESS_COOKIE_NAME, wrong_type_token)
    assert client.get("/api/v1/auth/me").status_code == 401

    # Login válido -> GET /me 200 con UserPublic de 7 campos
    client.cookies.clear()
    login_resp = client.post(
        "/api/v1/auth/token",
        data={"username": "cliente1", "password": "ClaveSegura123!"},
    )
    assert login_resp.status_code == 200
    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert set(me_data.keys()) == {
        "id",
        "username",
        "full_name",
        "email",
        "role",
        "disabled",
        "created_at",
    }
    assert me_data["username"] == "cliente1"

    # Desactivar usuario en BD tras login -> /me responde 400
    with Session(test_engine, expire_on_commit=False) as session:
        user_db = session.exec(select(Usuario).where(Usuario.username == "cliente1")).one()
        user_db.disabled = True
        session.add(user_db)
        session.commit()

    me_disabled = client.get("/api/v1/auth/me")
    assert me_disabled.status_code == 400
    assert me_disabled.json()["detail"] == "Cuenta de usuario desactivada"

    # Eliminar usuario de BD -> /me responde 401
    with Session(test_engine, expire_on_commit=False) as session:
        user_db = session.exec(select(Usuario).where(Usuario.username == "cliente1")).one()
        session.delete(user_db)
        session.commit()

    me_deleted = client.get("/api/v1/auth/me")
    assert me_deleted.status_code == 401


def test_logout_elimina_cookie_e_invalida_sesion(
    auth_client: tuple[TestClient, object],
) -> None:
    """POST /logout expira la cookie access_token y /me deja de autenticar."""
    client, _ = auth_client
    assert _register_sample_user(client).status_code == 201
    assert (
        client.post(
            "/api/v1/auth/token",
            data={"username": "cliente1", "password": "ClaveSegura123!"},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/me").status_code == 200

    logout_resp = client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200
    set_cookie = logout_resp.headers.get("set-cookie", "")
    assert f"{ACCESS_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Path=/" in set_cookie
    assert "samesite=lax" in set_cookie.lower()

    assert client.get("/api/v1/auth/me").status_code == 401
