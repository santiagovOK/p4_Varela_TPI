"""Pruebas unitarias y de integración para el módulo de Categorías (E5.1)."""

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
from app.modules.categorias.models import Categoria
from app.modules.productos.models import Producto
from app.modules.usuarios.models import Usuario


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


def _create_db_categoria(
    test_engine: object,
    *,
    nombre: str,
    descripcion: str | None = None,
    activo: bool = True,
) -> Categoria:
    """Inserta una categoría directamente en la base de prueba."""
    with Session(test_engine, expire_on_commit=False) as session:  # type: ignore[arg-type]
        categoria = Categoria(
            nombre=nombre,
            descripcion=descripcion,
            activo=activo,
        )
        session.add(categoria)
        session.commit()
        session.refresh(categoria)
        return categoria


def _auth_cookies(user: Usuario) -> dict[str, str]:
    """Genera cookies de sesión HttpOnly simuladas para el usuario."""
    token = create_access_token(user.username, role=user.role)
    return {ACCESS_COOKIE_NAME: token}


@pytest.fixture
def categorias_client(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, object]]:
    """Provee TestClient aislado sobre SQLite en memoria con StaticPool."""
    test_engine = _build_engine("sqlite:///:memory:")
    create_all_tables(test_engine)
    monkeypatch.setattr(
        "app.main.create_all_tables", lambda: create_all_tables(test_engine)
    )

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


def test_categorias_lectura_publica_solo_activas_y_detalle_404(
    categorias_client: tuple[TestClient, object],
) -> None:
    """GET /categorias y GET /categorias/{id} son públicos y filtran inactivas."""
    client, test_engine = categorias_client
    c1 = _create_db_categoria(test_engine, nombre="Empanadas", descripcion="Horneadas")
    c2 = _create_db_categoria(test_engine, nombre="Inactiva", activo=False)
    c3 = _create_db_categoria(test_engine, nombre="Bebidas", descripcion="Frías")

    resp_list = client.get("/api/v1/categorias")
    assert resp_list.status_code == 200
    data_list = resp_list.json()
    assert [item["id"] for item in data_list] == [c1.id, c3.id]
    assert all(item["activo"] is True for item in data_list)

    resp_ok = client.get(f"/api/v1/categorias/{c1.id}")
    assert resp_ok.status_code == 200
    assert resp_ok.json() == {
        "id": c1.id,
        "nombre": "Empanadas",
        "descripcion": "Horneadas",
        "activo": True,
    }

    assert client.get(f"/api/v1/categorias/{c2.id}").status_code == 404
    assert client.get("/api/v1/categorias/9999").status_code == 404


def test_categorias_post_permisos_normalizacion_y_duplicados(
    categorias_client: tuple[TestClient, object],
) -> None:
    """POST /categorias exige admin por cookie, normaliza y respeta unicidad."""
    client, test_engine = categorias_client
    admin = _create_db_user(
        test_engine, username="admin_cat", email="admin_cat@example.com", role="admin"
    )
    user = _create_db_user(
        test_engine, username="user_cat", email="user_cat@example.com", role="user"
    )
    disabled_admin = _create_db_user(
        test_engine,
        username="admin_off",
        email="admin_off@example.com",
        role="admin",
        disabled=True,
    )
    _create_db_categoria(test_engine, nombre="Archivada", activo=False)

    payload = {"nombre": "  Pizzas  ", "descripcion": "  A la piedra  "}

    assert client.post("/api/v1/categorias", json=payload).status_code == 401
    admin_token = create_access_token(admin.username, role=admin.role)
    assert (
        client.post(
            "/api/v1/categorias",
            json=payload,
            headers={"Authorization": f"Bearer {admin_token}"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/categorias", json=payload, cookies=_auth_cookies(user)
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/categorias", json=payload, cookies=_auth_cookies(disabled_admin)
        ).status_code
        == 400
    )

    resp_created = client.post(
        "/api/v1/categorias", json=payload, cookies=_auth_cookies(admin)
    )
    assert resp_created.status_code == 201
    created = resp_created.json()
    assert created["nombre"] == "Pizzas"
    assert created["descripcion"] == "A la piedra"
    assert created["activo"] is True

    # Validaciones de longitud / espacios
    assert (
        client.post(
            "/api/v1/categorias",
            json={"nombre": "   "},
            cookies=_auth_cookies(admin),
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/categorias",
            json={"nombre": " a "},
            cookies=_auth_cookies(admin),
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/categorias",
            json={"nombre": "A"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/categorias",
            json={"nombre": "X" * 101},
            cookies=_auth_cookies(admin),
        ).status_code
        == 422
    )

    # NombreDuplicado (409) contra activa y contra inactiva
    assert (
        client.post(
            "/api/v1/categorias",
            json={"nombre": "  Pizzas  "},
            cookies=_auth_cookies(admin),
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/categorias",
            json={"nombre": "Archivada"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 409
    )


def test_categorias_put_parcial_normalizacion_y_conflictos(
    categorias_client: tuple[TestClient, object],
) -> None:
    """PUT /categorias/{id} aplica actualización parcial, normaliza y valida conflictos."""
    client, test_engine = categorias_client
    admin = _create_db_user(
        test_engine, username="admin_put", email="admin_put@example.com", role="admin"
    )
    c1 = _create_db_categoria(test_engine, nombre="Sandwiches", descripcion="Calientes")
    _create_db_categoria(test_engine, nombre="Postres", descripcion="Dulces")
    inactiva = _create_db_categoria(test_engine, nombre="Antigua", activo=False)

    # Actualización parcial solo de descripcion
    resp_desc = client.put(
        f"/api/v1/categorias/{c1.id}",
        json={"descripcion": "  En pan casero  "},
        cookies=_auth_cookies(admin),
    )
    assert resp_desc.status_code == 200
    assert resp_desc.json()["nombre"] == "Sandwiches"
    assert resp_desc.json()["descripcion"] == "En pan casero"

    # Actualización parcial solo de nombre + envío del propio nombre
    resp_name = client.put(
        f"/api/v1/categorias/{c1.id}",
        json={"nombre": "  Lomitos  "},
        cookies=_auth_cookies(admin),
    )
    assert resp_name.status_code == 200
    assert resp_name.json()["nombre"] == "Lomitos"
    assert resp_name.json()["descripcion"] == "En pan casero"

    resp_same = client.put(
        f"/api/v1/categorias/{c1.id}",
        json={"nombre": "Lomitos"},
        cookies=_auth_cookies(admin),
    )
    assert resp_same.status_code == 200

    # Errores 400 / 404 / 409
    assert (
        client.put(
            f"/api/v1/categorias/{c1.id}",
            json={"nombre": "   "},
            cookies=_auth_cookies(admin),
        ).status_code
        == 400
    )
    assert (
        client.put(
            f"/api/v1/categorias/{c1.id}",
            json={"nombre": None},
            cookies=_auth_cookies(admin),
        ).status_code
        == 400
    )
    assert (
        client.put(
            f"/api/v1/categorias/{c1.id}",
            json={"nombre": "Postres"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/v1/categorias/{c1.id}",
            json={"nombre": "Antigua"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 409
    )
    assert (
        client.put(
            f"/api/v1/categorias/{inactiva.id}",
            json={"nombre": "Otra"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 404
    )
    assert (
        client.put(
            "/api/v1/categorias/9999",
            json={"nombre": "Otra"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 404
    )


def test_categorias_delete_logico_204_preserva_nombre_y_productos(
    categorias_client: tuple[TestClient, object],
) -> None:
    """DELETE /categorias/{id} da baja lógica 204 sin liberar nombre ni ocultar productos."""
    client, test_engine = categorias_client
    admin = _create_db_user(
        test_engine, username="admin_del", email="admin_del@example.com", role="admin"
    )
    user = _create_db_user(
        test_engine, username="user_del", email="user_del@example.com", role="user"
    )
    cat = _create_db_categoria(test_engine, nombre="Pastas")

    with Session(test_engine, expire_on_commit=False) as session:  # type: ignore[arg-type]
        prod = Producto(
            nombre="Ravioles",
            precio_base=4500.0,
            stock=10,
            disponible=True,
            activo=True,
            categoria_id=cat.id,  # type: ignore[arg-type]
        )
        session.add(prod)
        session.commit()
        session.refresh(prod)
        prod_id = prod.id

    assert client.delete(f"/api/v1/categorias/{cat.id}").status_code == 401
    assert (
        client.delete(
            f"/api/v1/categorias/{cat.id}", cookies=_auth_cookies(user)
        ).status_code
        == 403
    )

    resp_del = client.delete(
        f"/api/v1/categorias/{cat.id}", cookies=_auth_cookies(admin)
    )
    assert resp_del.status_code == 204
    assert resp_del.content == b""

    with Session(test_engine, expire_on_commit=False) as session:  # type: ignore[arg-type]
        db_cat = session.get(Categoria, cat.id)
        assert db_cat is not None
        assert db_cat.activo is False

    assert client.get(f"/api/v1/categorias/{cat.id}").status_code == 404
    assert (
        client.put(
            f"/api/v1/categorias/{cat.id}",
            json={"nombre": "Pastas Frescas"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/v1/categorias/{cat.id}", cookies=_auth_cookies(admin)
        ).status_code
        == 404
    )
    # Nombre único sigue reservado
    assert (
        client.post(
            "/api/v1/categorias",
            json={"nombre": "Pastas"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 409
    )
    # Producto asociado sigue visible en catálogo
    resp_prod = client.get(f"/api/v1/productos/{prod_id}")
    assert resp_prod.status_code == 200
    assert resp_prod.json()["categoria"]["activo"] is False


def test_categorias_ast_sin_commit_en_repository_service_router() -> None:
    """Verifica por AST que repository, service y router de categorias no llaman .commit()."""
    base_dir = Path(__file__).resolve().parent.parent / "app" / "modules" / "categorias"
    for filename in ("repository.py", "service.py", "router.py"):
        tree = ast.parse((base_dir / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr != "commit", (
                    f"{filename} no debe invocar .commit() directamente"
                )
