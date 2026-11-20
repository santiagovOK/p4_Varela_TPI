"""Pruebas unitarias y de integración para administración de usuarios (E4.4)."""

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.database import _build_engine, create_all_tables, get_session
from app.core.deps import ACCESS_COOKIE_NAME
from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.usuarios import (
    AutoDesactivacionNoPermitida,
    UserPublic,
    Usuario,
    UsuarioNoEncontrado,
    UsuarioRepository,
    UsuarioService,
    UsuarioUnitOfWork,
)

USER_PUBLIC_FIELDS = {
    "id",
    "username",
    "full_name",
    "email",
    "role",
    "disabled",
    "created_at",
}


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


@pytest.fixture
def admin_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, object]]:
    """Provee TestClient aislado sobre SQLite en memoria con StaticPool."""
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


def test_usuario_repository_queries_y_listado_deterministico() -> None:
    """UsuarioRepository resuelve get_by_username/get_by_email y lista todos por id ascendente."""
    test_engine = _build_engine("sqlite:///:memory:")
    create_all_tables(test_engine)
    try:
        u1 = _create_db_user(test_engine, username="zeta", email="zeta@example.com", role="admin")
        u2 = _create_db_user(test_engine, username="alfa", email="alfa@example.com", disabled=True)
        u3 = _create_db_user(test_engine, username="beta", email="beta@example.com", disabled=False)

        with Session(test_engine, expire_on_commit=False) as session:
            repo = UsuarioRepository(session)
            by_user = repo.get_by_username("  zeta  ")
            assert by_user is not None
            assert by_user.id == u1.id
            assert repo.get_by_username("inexistente") is None

            by_email = repo.get_by_email("  alfa@example.com  ")
            assert by_email is not None
            assert by_email.id == u2.id
            assert repo.get_by_email("nadie@example.com") is None

            listed = repo.list_all()
            listed_get_all = repo.get_all()
            assert [u.id for u in listed] == [u1.id, u2.id, u3.id]
            assert [u.id for u in listed_get_all] == [u1.id, u2.id, u3.id]
            assert any(u.disabled is True for u in listed)
    finally:
        test_engine.dispose()


def test_usuario_uow_y_service_commit_rollback_y_ausencia_de_commit_directo() -> None:
    """Verifica persistencia/rollback del UoW y ausencia de .commit( en repository/service/router."""
    test_engine = _build_engine("sqlite:///:memory:")
    create_all_tables(test_engine)
    try:
        admin = _create_db_user(test_engine, username="admin1", email="admin1@example.com", role="admin")
        cliente = _create_db_user(test_engine, username="cliente1", email="cliente1@example.com", role="user")

        def uow_factory() -> UsuarioUnitOfWork:
            return UsuarioUnitOfWork(lambda: Session(test_engine, expire_on_commit=False))

        service = UsuarioService(uow_factory())
        listado = service.list_usuarios()
        assert all(isinstance(item, UserPublic) for item in listado)
        assert [item.id for item in listado] == [admin.id, cliente.id]

        # Commit al salir sin error (expire_on_commit=False)
        desactivado = service.desactivar_usuario(cliente.id, current_user_id=admin.id)
        assert desactivado.disabled is True

        # Rollback ante excepción de dominio dentro del UoW
        with pytest.raises(AutoDesactivacionNoPermitida):
            with uow_factory() as uow:
                target = uow.usuarios.get_by_id(cliente.id)
                assert target is not None
                target.disabled = False
                uow.usuarios.update(target)
                raise AutoDesactivacionNoPermitida("abortar cambio")

        with Session(test_engine, expire_on_commit=False) as session:
            persisted = session.get(Usuario, cliente.id)
            assert persisted is not None
            assert persisted.disabled is True

        with pytest.raises(UsuarioNoEncontrado):
            service.activar_usuario(99999)
    finally:
        test_engine.dispose()

    usuarios_dir = Path(__file__).resolve().parent.parent / "app" / "modules" / "usuarios"
    for filename in ("repository.py", "service.py", "router.py"):
        tree = ast.parse((usuarios_dir / filename).read_text(encoding="utf-8"))
        commit_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "commit"
        ]
        assert not commit_calls, f"Se encontró llamada a .commit() inesperada en {filename}"


def test_admin_listar_usuarios_contratos_y_permisos(
    admin_client: tuple[TestClient, object],
) -> None:
    """GET /api/v1/admin/usuarios retorna 200 list[UserPublic] incluyendo desactivados y aplica 401/403/400."""
    client, test_engine = admin_client
    admin = _create_db_user(test_engine, username="admin_list", email="admin_list@example.com", role="admin")
    activo = _create_db_user(test_engine, username="u_activo", email="u_activo@example.com", role="user", disabled=False)
    inactivo = _create_db_user(test_engine, username="u_inactivo", email="u_inactivo@example.com", role="user", disabled=True)
    admin_disabled = _create_db_user(test_engine, username="admin_off", email="admin_off@example.com", role="admin", disabled=True)

    # 401 sin cookie
    assert client.get("/api/v1/admin/usuarios").status_code == 401

    # 401 enviando solo Authorization: Bearer
    admin_token = create_access_token({"sub": admin.username, "role": "admin"})
    assert (
        client.get(
            "/api/v1/admin/usuarios",
            headers={"Authorization": f"Bearer {admin_token}"},
        ).status_code
        == 401
    )

    # 403 con rol user
    client.cookies.set(ACCESS_COOKIE_NAME, create_access_token({"sub": activo.username, "role": "user"}))
    assert client.get("/api/v1/admin/usuarios").status_code == 403

    # 400 cuando el admin ejecutor está desactivado en BD
    client.cookies.set(ACCESS_COOKIE_NAME, create_access_token({"sub": admin_disabled.username, "role": "admin"}))
    resp_disabled = client.get("/api/v1/admin/usuarios")
    assert resp_disabled.status_code == 400
    assert resp_disabled.json()["detail"] == "Cuenta de usuario desactivada"

    # 200 con admin activo: incluye activos y desactivados en orden por id, exactamente 7 campos
    client.cookies.set(ACCESS_COOKIE_NAME, admin_token)
    resp_ok = client.get("/api/v1/admin/usuarios")
    assert resp_ok.status_code == 200
    payload = resp_ok.json()
    assert isinstance(payload, list)
    assert [item["id"] for item in payload] == [admin.id, activo.id, inactivo.id, admin_disabled.id]
    assert any(item["disabled"] is True for item in payload)
    for item in payload:
        assert set(item.keys()) == USER_PUBLIC_FIELDS
        assert "hashed_password" not in item
        assert "password" not in item


def test_admin_desactivar_usuario_casos_exitosos_idempotencia_y_errores(
    admin_client: tuple[TestClient, object],
) -> None:
    """POST /api/v1/admin/usuarios/{id}/desactivar cubre 200, idempotencia, 400 auto-desactivación, 404, 403, 401 y 400 ejecutor desactivado."""
    client, test_engine = admin_client
    admin1 = _create_db_user(test_engine, username="adm1", email="adm1@example.com", role="admin")
    admin2 = _create_db_user(test_engine, username="adm2", email="adm2@example.com", role="admin")
    cliente = _create_db_user(test_engine, username="cli1", email="cli1@example.com", role="user")
    admin_off = _create_db_user(test_engine, username="adm_off", email="adm_off@example.com", role="admin", disabled=True)

    # 401 sin cookie
    assert client.post(f"/api/v1/admin/usuarios/{cliente.id}/desactivar").status_code == 401

    # 403 con rol user
    cliente_token = create_access_token({"sub": cliente.username, "role": "user"})
    client.cookies.set(ACCESS_COOKIE_NAME, cliente_token)
    assert client.post(f"/api/v1/admin/usuarios/{admin2.id}/desactivar").status_code == 403

    # 400 si el admin ejecutor está desactivado en BD
    client.cookies.set(ACCESS_COOKIE_NAME, create_access_token({"sub": admin_off.username, "role": "admin"}))
    resp_exec_off = client.post(f"/api/v1/admin/usuarios/{cliente.id}/desactivar")
    assert resp_exec_off.status_code == 400
    assert resp_exec_off.json()["detail"] == "Cuenta de usuario desactivada"

    # Admin activo
    admin1_token = create_access_token({"sub": admin1.username, "role": "admin"})
    client.cookies.set(ACCESS_COOKIE_NAME, admin1_token)

    # 400 auto-desactivación (current_user.id == id) y persiste disabled=False en BD
    resp_self = client.post(f"/api/v1/admin/usuarios/{admin1.id}/desactivar")
    assert resp_self.status_code == 400
    with Session(test_engine, expire_on_commit=False) as session:
        db_admin1 = session.get(Usuario, admin1.id)
        assert db_admin1 is not None
        assert db_admin1.disabled is False

    # 404 si usuario no existe
    assert client.post("/api/v1/admin/usuarios/99999/desactivar").status_code == 404

    # 200 al desactivar usuario común + idempotencia + bloqueo inmediato de sesión del cliente
    resp_deact = client.post(f"/api/v1/admin/usuarios/{cliente.id}/desactivar")
    assert resp_deact.status_code == 200
    data = resp_deact.json()
    assert set(data.keys()) == USER_PUBLIC_FIELDS
    assert data["id"] == cliente.id
    assert data["disabled"] is True

    resp_deact_idem = client.post(f"/api/v1/admin/usuarios/{cliente.id}/desactivar")
    assert resp_deact_idem.status_code == 200
    assert resp_deact_idem.json()["disabled"] is True

    # También permite desactivar a otro admin distinto
    resp_deact_admin2 = client.post(f"/api/v1/admin/usuarios/{admin2.id}/desactivar")
    assert resp_deact_admin2.status_code == 200
    assert resp_deact_admin2.json()["disabled"] is True

    # El cliente desactivado ya no puede usar endpoints con sesión activa (400)
    client.cookies.set(ACCESS_COOKIE_NAME, cliente_token)
    resp_me_disabled = client.get("/api/v1/auth/me")
    assert resp_me_disabled.status_code == 400
    assert resp_me_disabled.json()["detail"] == "Cuenta de usuario desactivada"


def test_admin_activar_usuario_casos_exitosos_idempotencia_y_errores(
    admin_client: tuple[TestClient, object],
) -> None:
    """POST /api/v1/admin/usuarios/{id}/activar cubre 200, idempotencia, 404, 403, 401 y 400 ejecutor desactivado."""
    client, test_engine = admin_client
    admin = _create_db_user(test_engine, username="adm_act", email="adm_act@example.com", role="admin")
    cliente_off = _create_db_user(test_engine, username="cli_off", email="cli_off@example.com", role="user", disabled=True)
    cliente_on = _create_db_user(test_engine, username="cli_on", email="cli_on@example.com", role="user", disabled=False)
    admin_off = _create_db_user(test_engine, username="adm_off2", email="adm_off2@example.com", role="admin", disabled=True)

    # 401 sin cookie
    assert client.post(f"/api/v1/admin/usuarios/{cliente_off.id}/activar").status_code == 401

    # 403 con rol user
    client.cookies.set(ACCESS_COOKIE_NAME, create_access_token({"sub": cliente_on.username, "role": "user"}))
    assert client.post(f"/api/v1/admin/usuarios/{cliente_off.id}/activar").status_code == 403

    # 400 si el admin ejecutor está desactivado en BD
    client.cookies.set(ACCESS_COOKIE_NAME, create_access_token({"sub": admin_off.username, "role": "admin"}))
    resp_exec_off = client.post(f"/api/v1/admin/usuarios/{cliente_off.id}/activar")
    assert resp_exec_off.status_code == 400
    assert resp_exec_off.json()["detail"] == "Cuenta de usuario desactivada"

    # Admin activo
    client.cookies.set(ACCESS_COOKIE_NAME, create_access_token({"sub": admin.username, "role": "admin"}))

    # 404 si usuario no existe
    assert client.post("/api/v1/admin/usuarios/88888/activar").status_code == 404

    # 200 reactiva usuario desactivado + actualiza BD
    resp_act = client.post(f"/api/v1/admin/usuarios/{cliente_off.id}/activar")
    assert resp_act.status_code == 200
    data = resp_act.json()
    assert set(data.keys()) == USER_PUBLIC_FIELDS
    assert data["id"] == cliente_off.id
    assert data["disabled"] is False

    with Session(test_engine, expire_on_commit=False) as session:
        db_user = session.get(Usuario, cliente_off.id)
        assert db_user is not None
        assert db_user.disabled is False

    # Idempotente al activar usuario ya activo
    resp_act_idem = client.post(f"/api/v1/admin/usuarios/{cliente_off.id}/activar")
    assert resp_act_idem.status_code == 200
    assert resp_act_idem.json()["disabled"] is False
