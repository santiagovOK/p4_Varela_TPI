"""Pruebas unitarias y de integración para `app.core.deps` (E4.3)."""

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from sqlmodel import Session

from app.core.config import get_settings
from app.core.database import _build_engine, create_all_tables, get_session
from app.core.deps import (
    ACCESS_COOKIE_NAME,
    get_current_active_user,
    get_current_user,
    require_role,
)
from app.core.security import create_access_token, hash_password
from app.main import app as main_app
from app.modules.usuarios.models import Usuario


def _build_probe_app() -> FastAPI:
    """Construye una app FastAPI mínima para probar dependencias transversales."""
    probe = FastAPI()

    @probe.get("/probe/current-user")
    def probe_current_user(
        current_user: Annotated[Usuario, Depends(get_current_user)],
    ) -> dict[str, object]:
        return {
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role,
            "disabled": current_user.disabled,
        }

    @probe.get("/probe/active-user")
    def probe_active_user(
        current_user: Annotated[Usuario, Depends(get_current_active_user)],
    ) -> dict[str, object]:
        return {
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role,
            "disabled": current_user.disabled,
        }

    @probe.get("/probe/admin-list")
    def probe_admin_list(
        current_user: Annotated[Usuario, Depends(require_role(["admin"]))],
    ) -> dict[str, object]:
        return {
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role,
            "disabled": current_user.disabled,
        }

    @probe.get("/probe/admin-str")
    def probe_admin_str(
        current_user: Annotated[Usuario, Depends(require_role("admin"))],
    ) -> dict[str, object]:
        return {"id": current_user.id, "role": current_user.role}

    @probe.get("/probe/multi-role")
    def probe_multi_role(
        current_user: Annotated[Usuario, Depends(require_role(["user", "admin"]))],
    ) -> dict[str, object]:
        return {"id": current_user.id, "role": current_user.role}

    return probe


@pytest.fixture
def deps_client() -> Iterator[tuple[TestClient, object]]:
    """Provee TestClient aislado sobre SQLite en memoria con StaticPool."""
    test_engine = _build_engine("sqlite:///:memory:")
    create_all_tables(test_engine)
    probe_app = _build_probe_app()

    def override_get_session() -> Iterator[Session]:
        with Session(test_engine, expire_on_commit=False) as session:
            yield session

    probe_app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(probe_app) as client:
            yield client, test_engine
    finally:
        probe_app.dependency_overrides.clear()
        test_engine.dispose()


def _create_db_user(
    test_engine: object,
    *,
    username: str,
    email: str,
    role: str = "user",
    disabled: bool = False,
) -> Usuario:
    """Inserta un usuario en la base de prueba y lo retorna."""
    with Session(test_engine, expire_on_commit=False) as session:  # type: ignore[arg-type]
        user = Usuario(
            username=username,
            full_name=f"Nombre {username}",
            email=email,
            hashed_password=hash_password("ClaveSegura123!"),
            role=role,
            disabled=disabled,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def test_rechaza_sin_cookie_y_rechaza_authorization_bearer(
    deps_client: tuple[TestClient, object],
) -> None:
    """Sin cookie retorna 401; enviar solo Authorization: Bearer también retorna 401."""
    client, test_engine = deps_client
    _create_db_user(test_engine, username="ana", email="ana@example.com")
    token = create_access_token({"sub": "ana", "role": "user"})

    resp_no_auth = client.get("/probe/current-user")
    assert resp_no_auth.status_code == 401
    assert resp_no_auth.json()["detail"] == "No autenticado"
    assert resp_no_auth.headers.get("www-authenticate") == "Bearer"

    resp_bearer = client.get(
        "/probe/current-user",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_bearer.status_code == 401
    assert resp_bearer.json()["detail"] == "No autenticado"


def test_cookie_prevalece_sobre_authorization_bearer_invalido(
    deps_client: tuple[TestClient, object],
) -> None:
    """Usa exclusivamente la cookie `access_token` aunque Authorization sea inválido."""
    client, test_engine = deps_client
    user = _create_db_user(test_engine, username="luis", email="luis@example.com")
    token = create_access_token({"sub": user.username, "role": user.role})

    client.cookies.set(ACCESS_COOKIE_NAME, token)
    resp = client.get(
        "/probe/current-user",
        headers={"Authorization": "Bearer token-invalido"},
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "id": user.id,
        "username": "luis",
        "role": "user",
        "disabled": False,
    }


def test_get_current_user_rechaza_token_malformado_expirado_y_tipo_distinto(
    deps_client: tuple[TestClient, object],
) -> None:
    """Token malformado, expirado, sin sub válido o con type != 'access' retorna 401."""
    client, test_engine = deps_client
    _create_db_user(test_engine, username="marta", email="marta@example.com")
    settings = get_settings()

    # Malformado
    client.cookies.set(ACCESS_COOKIE_NAME, "no-es-un-jwt")
    assert client.get("/probe/current-user").status_code == 401

    # Firmado con otra clave
    wrong_key_token = jwt.encode(
        {
            "sub": "marta",
            "role": "user",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "otra-clave-secreta-distinta-de-32-chars",
        algorithm=settings.ALGORITHM,
    )
    client.cookies.set(ACCESS_COOKIE_NAME, wrong_key_token)
    assert client.get("/probe/current-user").status_code == 401

    # Expirado
    expired_token = create_access_token(
        {"sub": "marta", "role": "user"},
        expires_delta=timedelta(seconds=-5),
    )
    client.cookies.set(ACCESS_COOKIE_NAME, expired_token)
    assert client.get("/probe/current-user").status_code == 401

    # type="refresh"
    refresh_token = jwt.encode(
        {
            "sub": "marta",
            "role": "user",
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    client.cookies.set(ACCESS_COOKIE_NAME, refresh_token)
    assert client.get("/probe/current-user").status_code == 401

    # sub en blanco
    blank_sub_token = jwt.encode(
        {
            "sub": "   ",
            "role": "user",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    client.cookies.set(ACCESS_COOKIE_NAME, blank_sub_token)
    assert client.get("/probe/current-user").status_code == 401


def test_get_current_user_consulta_bd_autoritativamente(
    deps_client: tuple[TestClient, object],
) -> None:
    """Usuario eliminado retorna 401 y cambios de rol en BD se reflejan en cada request."""
    client, test_engine = deps_client
    user = _create_db_user(test_engine, username="sofi", email="sofi@example.com", role="user")
    token = create_access_token({"sub": "sofi", "role": "user"})
    client.cookies.set(ACCESS_COOKIE_NAME, token)

    # Cambio autoritativo de rol en BD sin re-emitir token
    with Session(test_engine, expire_on_commit=False) as session:  # type: ignore[arg-type]
        db_user = session.get(Usuario, user.id)
        assert db_user is not None
        db_user.role = "admin"
        session.add(db_user)
        session.commit()

    resp = client.get("/probe/current-user")
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"

    # Usuario eliminado de la BD -> 401
    with Session(test_engine, expire_on_commit=False) as session:  # type: ignore[arg-type]
        db_user = session.get(Usuario, user.id)
        assert db_user is not None
        session.delete(db_user)
        session.commit()

    assert client.get("/probe/current-user").status_code == 401


def test_get_current_active_user_rechaza_desactivado_con_400(
    deps_client: tuple[TestClient, object],
) -> None:
    """Si disabled=True en BD, get_current_active_user responde 400."""
    client, test_engine = deps_client
    user = _create_db_user(test_engine, username="diego", email="diego@example.com")
    token = create_access_token({"sub": "diego", "role": "user"})
    client.cookies.set(ACCESS_COOKIE_NAME, token)

    assert client.get("/probe/active-user").status_code == 200

    with Session(test_engine, expire_on_commit=False) as session:  # type: ignore[arg-type]
        db_user = session.get(Usuario, user.id)
        assert db_user is not None
        db_user.disabled = True
        session.add(db_user)
        session.commit()

    resp_disabled = client.get("/probe/active-user")
    assert resp_disabled.status_code == 400
    assert resp_disabled.json()["detail"] == "Cuenta de usuario desactivada"


def test_require_role_autoriza_y_rechaza_segun_rol_y_estado(
    deps_client: tuple[TestClient, object],
) -> None:
    """require_role valida 401 sin cookie, 400 desactivado, 403 rol ajeno y 200 autorizado."""
    client, test_engine = deps_client
    cliente = _create_db_user(test_engine, username="cliente", email="cli@example.com", role="user")
    admin = _create_db_user(test_engine, username="admin1", email="adm@example.com", role="admin")
    desactivado = _create_db_user(
        test_engine,
        username="inactivo",
        email="inactivo@example.com",
        role="admin",
        disabled=True,
    )

    # Sin cookie -> 401
    assert client.get("/probe/admin-list").status_code == 401

    # Admin desactivado -> 400
    client.cookies.set(ACCESS_COOKIE_NAME, create_access_token({"sub": desactivado.username, "role": "admin"}))
    resp_inactivo = client.get("/probe/admin-list")
    assert resp_inactivo.status_code == 400
    assert resp_inactivo.json()["detail"] == "Cuenta de usuario desactivada"

    # Usuario común en ruta admin -> 403
    client.cookies.set(ACCESS_COOKIE_NAME, create_access_token({"sub": cliente.username, "role": "user"}))
    resp_forbidden = client.get("/probe/admin-list")
    assert resp_forbidden.status_code == 403
    assert resp_forbidden.json()["detail"] == "No tiene permisos suficientes para realizar esta acción"
    assert client.get("/probe/admin-str").status_code == 403

    # Usuario común en ruta multi-rol -> 200
    resp_multi = client.get("/probe/multi-role")
    assert resp_multi.status_code == 200
    assert resp_multi.json() == {"id": cliente.id, "role": "user"}

    # Admin activo -> 200 exponiendo id, username, role, disabled
    client.cookies.set(ACCESS_COOKIE_NAME, create_access_token({"sub": admin.username, "role": "admin"}))
    resp_admin = client.get("/probe/admin-list")
    assert resp_admin.status_code == 200
    assert resp_admin.json() == {
        "id": admin.id,
        "username": "admin1",
        "role": "admin",
        "disabled": False,
    }
    assert client.get("/probe/admin-str").status_code == 200


def test_require_role_rechaza_lista_vacia() -> None:
    """require_role sin roles válidos lanza ValueError."""
    with pytest.raises(ValueError):
        require_role([])
    with pytest.raises(ValueError):
        require_role("   ")


def test_integracion_auth_me_usa_get_current_active_user_y_override_de_sesion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/v1/auth/me usa get_current_active_user de app.core.deps y respeta override get_session."""
    test_engine = _build_engine("sqlite:///:memory:")
    create_all_tables(test_engine)
    monkeypatch.setattr("app.main.create_all_tables", lambda: create_all_tables(test_engine))

    def override_get_session() -> Iterator[Session]:
        with Session(test_engine, expire_on_commit=False) as session:
            yield session

    main_app.dependency_overrides[get_session] = override_get_session
    try:
        user = _create_db_user(test_engine, username="integrado", email="int@example.com")
        token = create_access_token({"sub": user.username, "role": user.role})

        with TestClient(main_app) as client:
            # Rechaza Bearer sin cookie
            resp_bearer = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp_bearer.status_code == 401

            # Acepta cookie y retorna UserPublic de 7 campos
            client.cookies.set(ACCESS_COOKIE_NAME, token)
            resp_ok = client.get("/api/v1/auth/me")
            assert resp_ok.status_code == 200
            data = resp_ok.json()
            assert set(data.keys()) == {
                "id",
                "username",
                "full_name",
                "email",
                "role",
                "disabled",
                "created_at",
            }
            assert data["username"] == "integrado"
            assert "hashed_password" not in data
    finally:
        main_app.dependency_overrides.clear()
        test_engine.dispose()
