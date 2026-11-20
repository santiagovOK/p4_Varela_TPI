"""Pruebas unitarias y de integración para el módulo de Productos (E5.2–E5.3)."""

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
    activo: bool = True,
) -> Categoria:
    """Inserta una categoría en la base de prueba."""
    with Session(test_engine, expire_on_commit=False) as session:  # type: ignore[arg-type]
        categoria = Categoria(nombre=nombre, activo=activo)
        session.add(categoria)
        session.commit()
        session.refresh(categoria)
        return categoria


def _create_db_producto(
    test_engine: object,
    *,
    nombre: str,
    categoria_id: int,
    precio_base: float = 1000.0,
    stock: int = 5,
    disponible: bool = True,
    activo: bool = True,
    descripcion: str | None = None,
) -> Producto:
    """Inserta un producto en la base de prueba."""
    with Session(test_engine, expire_on_commit=False) as session:  # type: ignore[arg-type]
        producto = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio_base=precio_base,
            stock=stock,
            disponible=disponible,
            activo=activo,
            categoria_id=categoria_id,
        )
        session.add(producto)
        session.commit()
        session.refresh(producto)
        return producto


def _auth_cookies(user: Usuario) -> dict[str, str]:
    """Genera cookies de sesión HttpOnly simuladas para el usuario."""
    token = create_access_token(user.username, role=user.role)
    return {ACCESS_COOKIE_NAME: token}


@pytest.fixture
def productos_client(
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


def test_productos_listado_paginado_filtros_y_detalle_publico(
    productos_client: tuple[TestClient, object],
) -> None:
    """GET /productos retorna {total, items} con filtros y excluye inactivos."""
    client, test_engine = productos_client
    cat_pizzas = _create_db_categoria(test_engine, nombre="Pizzas")
    cat_bebidas = _create_db_categoria(test_engine, nombre="Bebidas")

    p1 = _create_db_producto(
        test_engine,
        nombre="Pizza Muzzarella",
        categoria_id=cat_pizzas.id,  # type: ignore[arg-type]
        precio_base=8500.0,
        disponible=True,
        activo=True,
    )
    p2 = _create_db_producto(
        test_engine,
        nombre="Pizza Fugazzeta",
        categoria_id=cat_pizzas.id,  # type: ignore[arg-type]
        precio_base=9200.0,
        disponible=False,
        activo=True,
    )
    p3 = _create_db_producto(
        test_engine,
        nombre="Gaseosa Cola",
        categoria_id=cat_bebidas.id,  # type: ignore[arg-type]
        precio_base=2500.0,
        disponible=True,
        activo=True,
    )
    p_inactivo = _create_db_producto(
        test_engine,
        nombre="Pizza Oculta",
        categoria_id=cat_pizzas.id,  # type: ignore[arg-type]
        disponible=True,
        activo=False,
    )

    # Listado general público
    resp_all = client.get("/api/v1/productos")
    assert resp_all.status_code == 200
    body_all = resp_all.json()
    assert body_all["total"] == 3
    assert [item["id"] for item in body_all["items"]] == [p1.id, p2.id, p3.id]
    assert body_all["items"][0]["categoria"]["nombre"] == "Pizzas"

    # Paginación skip/limit y validación de límites
    resp_page = client.get("/api/v1/productos?skip=1&limit=1")
    assert resp_page.status_code == 200
    assert resp_page.json()["total"] == 3
    assert [item["id"] for item in resp_page.json()["items"]] == [p2.id]

    assert client.get("/api/v1/productos?limit=101").status_code == 422
    assert client.get("/api/v1/productos?skip=-1").status_code == 422

    # Búsqueda case-insensitive
    resp_search = client.get("/api/v1/productos?search=pizza")
    assert resp_search.status_code == 200
    assert resp_search.json()["total"] == 2
    assert [item["id"] for item in resp_search.json()["items"]] == [p1.id, p2.id]

    # Filtro por categoria_id y disponible
    resp_filt = client.get(
        f"/api/v1/productos?categoria_id={cat_pizzas.id}&disponible=true"
    )
    assert resp_filt.status_code == 200
    assert resp_filt.json()["total"] == 1
    assert [item["id"] for item in resp_filt.json()["items"]] == [p1.id]

    resp_no_disp = client.get("/api/v1/productos?disponible=false")
    assert resp_no_disp.status_code == 200
    assert [item["id"] for item in resp_no_disp.json()["items"]] == [p2.id]

    # Detalle público
    resp_det = client.get(f"/api/v1/productos/{p1.id}")
    assert resp_det.status_code == 200
    assert resp_det.json()["categoria"]["id"] == cat_pizzas.id
    assert client.get(f"/api/v1/productos/{p_inactivo.id}").status_code == 404
    assert client.get("/api/v1/productos/9999").status_code == 404


def test_productos_post_permisos_normalizacion_y_categoria_activa(
    productos_client: tuple[TestClient, object],
) -> None:
    """POST /productos exige admin, normaliza .strip() y valida categoría activa."""
    client, test_engine = productos_client
    admin = _create_db_user(
        test_engine, username="admin_prod", email="admin_prod@example.com", role="admin"
    )
    user = _create_db_user(
        test_engine, username="user_prod", email="user_prod@example.com", role="user"
    )
    cat_activa = _create_db_categoria(test_engine, nombre="Hamburguesas")
    cat_inactiva = _create_db_categoria(
        test_engine, nombre="Descontinuada", activo=False
    )

    payload = {
        "nombre": "  Burger Doble  ",
        "descripcion": "  Con cheddar  ",
        "precio_base": 7500.5,
        "imagen_url": "  https://cdn.example.com/burger.png  ",
        "stock": 12,
        "disponible": True,
        "categoria_id": cat_activa.id,
    }

    assert client.post("/api/v1/productos", json=payload).status_code == 401
    assert (
        client.post(
            "/api/v1/productos", json=payload, cookies=_auth_cookies(user)
        ).status_code
        == 403
    )

    resp_ok = client.post(
        "/api/v1/productos", json=payload, cookies=_auth_cookies(admin)
    )
    assert resp_ok.status_code == 201
    created = resp_ok.json()
    assert created["nombre"] == "Burger Doble"
    assert created["descripcion"] == "Con cheddar"
    assert created["imagen_url"] == "https://cdn.example.com/burger.png"
    assert created["stock"] == 12
    assert created["categoria"]["id"] == cat_activa.id
    assert created["categoria"]["nombre"] == "Hamburguesas"

    # Nombre con solo espacios -> 400
    assert (
        client.post(
            "/api/v1/productos",
            json={**payload, "nombre": "   "},
            cookies=_auth_cookies(admin),
        ).status_code
        == 400
    )

    # Categoría inexistente o inactiva -> 404 CategoriaNoEncontrada
    assert (
        client.post(
            "/api/v1/productos",
            json={**payload, "categoria_id": 9999},
            cookies=_auth_cookies(admin),
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/productos",
            json={**payload, "categoria_id": cat_inactiva.id},
            cookies=_auth_cookies(admin),
        ).status_code
        == 404
    )


def test_productos_put_parcial_recarga_categoria_y_errores(
    productos_client: tuple[TestClient, object],
) -> None:
    """PUT /productos/{id} aplica actualización parcial y recarga categoria."""
    client, test_engine = productos_client
    admin = _create_db_user(
        test_engine, username="admin_upd", email="admin_upd@example.com", role="admin"
    )
    cat1 = _create_db_categoria(test_engine, nombre="Cafetería")
    cat2 = _create_db_categoria(test_engine, nombre="Panadería")
    cat_inactiva = _create_db_categoria(test_engine, nombre="Oculta", activo=False)

    prod = _create_db_producto(
        test_engine,
        nombre="Medialuna",
        descripcion="De manteca",
        precio_base=900.0,
        stock=20,
        categoria_id=cat1.id,  # type: ignore[arg-type]
    )
    prod_inactivo = _create_db_producto(
        test_engine,
        nombre="Inactivo",
        categoria_id=cat1.id,  # type: ignore[arg-type]
        activo=False,
    )

    # Actualización parcial solo de precio_base y categoria_id
    resp_upd = client.put(
        f"/api/v1/productos/{prod.id}",
        json={"precio_base": 1100.0, "categoria_id": cat2.id},
        cookies=_auth_cookies(admin),
    )
    assert resp_upd.status_code == 200
    updated = resp_upd.json()
    assert updated["nombre"] == "Medialuna"
    assert updated["descripcion"] == "De manteca"
    assert updated["precio_base"] == 1100.0
    assert updated["stock"] == 20
    assert updated["categoria_id"] == cat2.id
    assert updated["categoria"]["id"] == cat2.id
    assert updated["categoria"]["nombre"] == "Panadería"

    # Validaciones 400 y 404
    assert (
        client.put(
            f"/api/v1/productos/{prod.id}",
            json={"nombre": "   "},
            cookies=_auth_cookies(admin),
        ).status_code
        == 400
    )
    assert (
        client.put(
            f"/api/v1/productos/{prod.id}",
            json={"precio_base": None},
            cookies=_auth_cookies(admin),
        ).status_code
        == 400
    )
    assert (
        client.put(
            f"/api/v1/productos/{prod.id}",
            json={"categoria_id": cat_inactiva.id},
            cookies=_auth_cookies(admin),
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/v1/productos/{prod.id}",
            json={"categoria_id": 9999},
            cookies=_auth_cookies(admin),
        ).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/v1/productos/{prod_inactivo.id}",
            json={"precio_base": 1500.0},
            cookies=_auth_cookies(admin),
        ).status_code
        == 404
    )
    assert (
        client.put(
            "/api/v1/productos/9999",
            json={"precio_base": 1500.0},
            cookies=_auth_cookies(admin),
        ).status_code
        == 404
    )


def test_productos_patch_stock_permisos_validacion_y_errores(
    productos_client: tuple[TestClient, object],
) -> None:
    """PATCH /productos/{id}/stock exige admin, valida stock >= 0 y recarga categoria."""
    client, test_engine = productos_client
    admin = _create_db_user(
        test_engine, username="admin_stk", email="admin_stk@example.com", role="admin"
    )
    user = _create_db_user(
        test_engine, username="user_stk", email="user_stk@example.com", role="user"
    )
    cat = _create_db_categoria(test_engine, nombre="Empanadas")
    prod = _create_db_producto(
        test_engine,
        nombre="Empanada de Carne",
        categoria_id=cat.id,  # type: ignore[arg-type]
        stock=10,
        disponible=True,
    )
    prod_inactivo = _create_db_producto(
        test_engine,
        nombre="Empanada Inactiva",
        categoria_id=cat.id,  # type: ignore[arg-type]
        activo=False,
    )

    payload_agotado = {"stock": 0, "disponible": False}
    assert (
        client.patch(
            f"/api/v1/productos/{prod.id}/stock", json=payload_agotado
        ).status_code
        == 401
    )
    assert (
        client.patch(
            f"/api/v1/productos/{prod.id}/stock",
            json=payload_agotado,
            cookies=_auth_cookies(user),
        ).status_code
        == 403
    )

    resp_zero = client.patch(
        f"/api/v1/productos/{prod.id}/stock",
        json=payload_agotado,
        cookies=_auth_cookies(admin),
    )
    assert resp_zero.status_code == 200
    body_zero = resp_zero.json()
    assert body_zero["stock"] == 0
    assert body_zero["disponible"] is False
    assert body_zero["categoria"]["id"] == cat.id
    assert body_zero["categoria"]["nombre"] == "Empanadas"

    resp_restock = client.patch(
        f"/api/v1/productos/{prod.id}/stock",
        json={"stock": 35, "disponible": True},
        cookies=_auth_cookies(admin),
    )
    assert resp_restock.status_code == 200
    body_restock = resp_restock.json()
    assert body_restock["stock"] == 35
    assert body_restock["disponible"] is True
    assert body_restock["categoria"]["nombre"] == "Empanadas"

    # Validación Pydantic 422 (stock < 0 o payload incompleto)
    assert (
        client.patch(
            f"/api/v1/productos/{prod.id}/stock",
            json={"stock": -1, "disponible": True},
            cookies=_auth_cookies(admin),
        ).status_code
        == 422
    )
    assert (
        client.patch(
            f"/api/v1/productos/{prod.id}/stock",
            json={"stock": 5},
            cookies=_auth_cookies(admin),
        ).status_code
        == 422
    )

    # Producto inexistente o inactivo -> 404
    assert (
        client.patch(
            "/api/v1/productos/9999/stock",
            json={"stock": 5, "disponible": True},
            cookies=_auth_cookies(admin),
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/productos/{prod_inactivo.id}/stock",
            json={"stock": 5, "disponible": True},
            cookies=_auth_cookies(admin),
        ).status_code
        == 404
    )


def test_productos_delete_baja_logica_204_e_invisibilidad_posterior(
    productos_client: tuple[TestClient, object],
) -> None:
    """DELETE /productos/{id} exige admin, retorna 204 sin cuerpo y aplica baja lógica."""
    client, test_engine = productos_client
    admin = _create_db_user(
        test_engine, username="admin_del", email="admin_del@example.com", role="admin"
    )
    user = _create_db_user(
        test_engine, username="user_del", email="user_del@example.com", role="user"
    )
    cat = _create_db_categoria(test_engine, nombre="Postres")
    prod = _create_db_producto(
        test_engine,
        nombre="Flan Casero",
        categoria_id=cat.id,  # type: ignore[arg-type]
        stock=8,
    )

    assert client.delete(f"/api/v1/productos/{prod.id}").status_code == 401
    assert (
        client.delete(
            f"/api/v1/productos/{prod.id}", cookies=_auth_cookies(user)
        ).status_code
        == 403
    )

    resp_del = client.delete(
        f"/api/v1/productos/{prod.id}", cookies=_auth_cookies(admin)
    )
    assert resp_del.status_code == 204
    assert resp_del.content == b""

    # Segundo DELETE y lecturas/escrituras posteriores -> 404 y excluido de listado
    assert (
        client.delete(
            f"/api/v1/productos/{prod.id}", cookies=_auth_cookies(admin)
        ).status_code
        == 404
    )
    assert client.get(f"/api/v1/productos/{prod.id}").status_code == 404
    assert (
        client.put(
            f"/api/v1/productos/{prod.id}",
            json={"precio_base": 2000.0},
            cookies=_auth_cookies(admin),
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/productos/{prod.id}/stock",
            json={"stock": 12, "disponible": True},
            cookies=_auth_cookies(admin),
        ).status_code
        == 404
    )

    resp_list = client.get("/api/v1/productos")
    assert resp_list.status_code == 200
    assert resp_list.json()["total"] == 0
    assert resp_list.json()["items"] == []

    # El registro persiste físicamente en BD con activo=False
    with Session(test_engine) as session:  # type: ignore[arg-type]
        persisted = session.get(Producto, prod.id)
        assert persisted is not None
        assert persisted.activo is False


def test_productos_ast_sin_commit_en_repository_service_router() -> None:
    """Verifica por AST que repository, service y router de productos no llaman .commit()."""
    base_dir = Path(__file__).resolve().parent.parent / "app" / "modules" / "productos"
    for filename in ("repository.py", "service.py", "router.py"):
        tree = ast.parse((base_dir / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr != "commit", (
                    f"{filename} no debe invocar .commit() directamente"
                )
