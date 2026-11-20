"""Pruebas unitarias y de integración HTTP para creación transaccional de pedidos (E6.1)."""

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.database import _build_engine, create_all_tables, get_session
from app.core.deps import ACCESS_COOKIE_NAME
from app.core.security import create_access_token, hash_password
from app.main import app
from app.modules.categorias.models import Categoria
from app.modules.pedidos.models import DetallePedido, Pedido
from app.modules.pedidos.schemas import ItemPedidoCreate, PedidoCreate
from app.modules.pedidos.service import DatosPedidoInvalidos, PedidoService
from app.modules.pedidos.unit_of_work import PedidoUnitOfWork
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
    stock: int = 10,
    disponible: bool = True,
    activo: bool = True,
) -> Producto:
    """Inserta un producto en la base de prueba."""
    with Session(test_engine, expire_on_commit=False) as session:  # type: ignore[arg-type]
        producto = Producto(
            nombre=nombre,
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
def pedidos_client(
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


def test_crear_pedido_requiere_sesion_activa(
    pedidos_client: tuple[TestClient, object],
) -> None:
    """POST /pedidos exige cookie HttpOnly access_token y usuario habilitado."""
    client, test_engine = pedidos_client
    cat = _create_db_categoria(test_engine, nombre="Pizzas")
    prod = _create_db_producto(
        test_engine, nombre="Muzzarella", categoria_id=cat.id  # type: ignore[arg-type]
    )
    payload = {
        "items": [{"producto_id": prod.id, "cantidad": 1}],
        "forma_pago": "EFECTIVO",
        "direccion_entrega": "Av. Colón 1234",
    }

    # Sin cookie -> 401
    resp_anon = client.post("/api/v1/pedidos", json=payload)
    assert resp_anon.status_code == 401

    # Con Bearer sin cookie -> 401
    user_ok = _create_db_user(test_engine, username="cliente1", email="c1@test.com")
    token = create_access_token(user_ok.username, role=user_ok.role)
    resp_bearer = client.post(
        "/api/v1/pedidos",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_bearer.status_code == 401

    # Usuario desactivado -> 400
    user_disabled = _create_db_user(
        test_engine,
        username="desactivado",
        email="dis@test.com",
        disabled=True,
    )
    resp_disabled = client.post(
        "/api/v1/pedidos",
        json=payload,
        cookies=_auth_cookies(user_disabled),
    )
    assert resp_disabled.status_code == 400
    assert resp_disabled.json()["detail"] == "Cuenta de usuario desactivada"


def test_crear_pedido_exitoso_descuenta_stock_y_snapshot_inmutable(
    pedidos_client: tuple[TestClient, object],
) -> None:
    """Crea pedido PENDIENTE, descuenta stock, normaliza texto e ignora campos manipulados."""
    client, test_engine = pedidos_client
    cliente = _create_db_user(test_engine, username="cliente", email="cli@test.com")
    admin = _create_db_user(
        test_engine, username="admin1", email="adm@test.com", role="admin"
    )
    cat = _create_db_categoria(test_engine, nombre="Comidas")
    p1 = _create_db_producto(
        test_engine,
        nombre="Empanada Carne",
        categoria_id=cat.id,  # type: ignore[arg-type]
        precio_base=1200.5,
        stock=10,
    )
    p2 = _create_db_producto(
        test_engine,
        nombre="Gaseosa 1.5L",
        categoria_id=cat.id,  # type: ignore[arg-type]
        precio_base=2500.0,
        stock=6,
    )

    # Cliente crea pedido con campos extra manipulados y espacios externos
    resp_user = client.post(
        "/api/v1/pedidos",
        json={
            "items": [
                {
                    "producto_id": p1.id,
                    "cantidad": 3,
                    "precio_unitario": 1.0,
                    "subtotal": 1.0,
                },
                {"producto_id": p2.id, "cantidad": 2},
            ],
            "forma_pago": "TRANSFERENCIA",
            "direccion_entrega": "  Av. San Martín 550  ",
            "notas": "  Sin timbre  ",
            "total": 1.0,
            "estado": "ENTREGADO",
            "usuario_id": 9999,
        },
        cookies=_auth_cookies(cliente),
    )
    assert resp_user.status_code == 201
    data = resp_user.json()
    assert data["usuario_id"] == cliente.id
    assert data["estado"] == "PENDIENTE"
    assert data["forma_pago"] == "TRANSFERENCIA"
    assert data["direccion_entrega"] == "Av. San Martín 550"
    assert data["notas"] == "Sin timbre"
    assert len(data["items"]) == 2
    assert data["items"][0]["nombre_producto"] == "Empanada Carne"
    assert data["items"][0]["precio_unitario"] == 1200.5
    assert data["items"][0]["subtotal"] == 3601.5
    assert data["items"][1]["subtotal"] == 5000.0
    assert data["total"] == 8601.5

    # Verificar descuento de stock en BD
    with Session(test_engine) as session:  # type: ignore[arg-type]
        p1_db = session.get(Producto, p1.id)
        p2_db = session.get(Producto, p2.id)
        assert p1_db is not None and p1_db.stock == 7
        assert p2_db is not None and p2_db.stock == 4

        # Mutar producto posteriormente (nombre, precio y baja lógica) no afecta snapshot (RN-05)
        p1_db.nombre = "Empanada Modificada"
        p1_db.precio_base = 9999.0
        p1_db.activo = False
        session.add(p1_db)
        session.commit()

        detalle = session.exec(
            select(DetallePedido).where(
                DetallePedido.pedido_id == data["id"],
                DetallePedido.producto_id == p1.id,
            )
        ).one()
        assert detalle.nombre_producto == "Empanada Carne"
        assert detalle.precio_unitario == 1200.5
        assert detalle.subtotal == 3601.5

    # Admin también puede crear pedidos en EFECTIVO
    resp_admin = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": p2.id, "cantidad": 1}],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Calle Falsa 123",
            "notas": "   ",
        },
        cookies=_auth_cookies(admin),
    )
    assert resp_admin.status_code == 201
    admin_data = resp_admin.json()
    assert admin_data["usuario_id"] == admin.id
    assert admin_data["estado"] == "PENDIENTE"
    assert admin_data["notas"] is None
    assert admin_data["total"] == 2500.0


def test_crear_pedido_validaciones_rn01_y_rn06(
    pedidos_client: tuple[TestClient, object],
) -> None:
    """Valida errores 422, 400 y 404 para datos inválidos, repetidos y estados de producto."""
    client, test_engine = pedidos_client
    user = _create_db_user(test_engine, username="val_user", email="val@test.com")
    cookies = _auth_cookies(user)
    cat = _create_db_categoria(test_engine, nombre="Bebidas")

    prod_ok = _create_db_producto(
        test_engine,
        nombre="Agua",
        categoria_id=cat.id,  # type: ignore[arg-type]
        stock=5,
    )
    prod_inactivo = _create_db_producto(
        test_engine,
        nombre="Baja",
        categoria_id=cat.id,  # type: ignore[arg-type]
        activo=False,
    )
    prod_no_disp = _create_db_producto(
        test_engine,
        nombre="SinDisp",
        categoria_id=cat.id,  # type: ignore[arg-type]
        disponible=False,
    )

    # 422: items vacío, cantidad < 1, forma_pago inválida, direccion < 5 cruda
    assert (
        client.post(
            "/api/v1/pedidos",
            json={
                "items": [],
                "forma_pago": "EFECTIVO",
                "direccion_entrega": "Av. Colón 123",
            },
            cookies=cookies,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/pedidos",
            json={
                "items": [{"producto_id": prod_ok.id, "cantidad": 0}],
                "forma_pago": "EFECTIVO",
                "direccion_entrega": "Av. Colón 123",
            },
            cookies=cookies,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/pedidos",
            json={
                "items": [{"producto_id": prod_ok.id, "cantidad": 1}],
                "forma_pago": "TARJETA",
                "direccion_entrega": "Av. Colón 123",
            },
            cookies=cookies,
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/pedidos",
            json={
                "items": [{"producto_id": prod_ok.id, "cantidad": 1}],
                "forma_pago": "EFECTIVO",
                "direccion_entrega": "1234",
            },
            cookies=cookies,
        ).status_code
        == 422
    )

    # 400: dirección con >= 5 caracteres crudos pero < 5 tras .strip()
    resp_espacios = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": prod_ok.id, "cantidad": 1}],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "  ab  ",
        },
        cookies=cookies,
    )
    assert resp_espacios.status_code == 400

    # 400: producto repetido
    resp_rep = client.post(
        "/api/v1/pedidos",
        json={
            "items": [
                {"producto_id": prod_ok.id, "cantidad": 1},
                {"producto_id": prod_ok.id, "cantidad": 2},
            ],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Av. Colón 123",
        },
        cookies=cookies,
    )
    assert resp_rep.status_code == 400

    # 404: producto inexistente o inactivo
    resp_inexist = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": 99999, "cantidad": 1}],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Av. Colón 123",
        },
        cookies=cookies,
    )
    assert resp_inexist.status_code == 404

    resp_inact = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": prod_inactivo.id, "cantidad": 1}],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Av. Colón 123",
        },
        cookies=cookies,
    )
    assert resp_inact.status_code == 404

    # 400: producto no disponible
    resp_no_disp = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": prod_no_disp.id, "cantidad": 1}],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Av. Colón 123",
        },
        cookies=cookies,
    )
    assert resp_no_disp.status_code == 400

    # 400: stock insuficiente
    resp_stock = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": prod_ok.id, "cantidad": 6}],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Av. Colón 123",
        },
        cookies=cookies,
    )
    assert resp_stock.status_code == 400

    # Verificar que no se creó ningún pedido ni se descontó stock
    with Session(test_engine) as session:  # type: ignore[arg-type]
        assert session.exec(select(Pedido)).all() == []
        prod_db = session.get(Producto, prod_ok.id)
        assert prod_db is not None and prod_db.stock == 5


def test_crear_pedido_rollback_total_si_falla_segunda_linea(
    pedidos_client: tuple[TestClient, object],
) -> None:
    """Fallo en segunda línea revierte pedido, líneas previas y descuento de stock de la primera."""
    client, test_engine = pedidos_client
    user = _create_db_user(test_engine, username="rb_user", email="rb@test.com")
    cat = _create_db_categoria(test_engine, nombre="Minutas")
    p1 = _create_db_producto(
        test_engine,
        nombre="Milanesa",
        categoria_id=cat.id,  # type: ignore[arg-type]
        precio_base=3000.0,
        stock=10,
    )
    p2 = _create_db_producto(
        test_engine,
        nombre="Papas",
        categoria_id=cat.id,  # type: ignore[arg-type]
        precio_base=1500.0,
        stock=1,
    )

    resp = client.post(
        "/api/v1/pedidos",
        json={
            "items": [
                {"producto_id": p1.id, "cantidad": 3},
                {"producto_id": p2.id, "cantidad": 2},
            ],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Bv. Illia 450",
        },
        cookies=_auth_cookies(user),
    )
    assert resp.status_code == 400

    with Session(test_engine) as session:  # type: ignore[arg-type]
        assert session.exec(select(Pedido)).all() == []
        assert session.exec(select(DetallePedido)).all() == []
        p1_db = session.get(Producto, p1.id)
        p2_db = session.get(Producto, p2.id)
        assert p1_db is not None and p1_db.stock == 10
        assert p2_db is not None and p2_db.stock == 1


def test_pedido_service_valida_solo_espacios_directamente() -> None:
    """Prueba unitaria directa sobre PedidoService para dirección solo espacios."""
    engine = _build_engine("sqlite:///:memory:")
    create_all_tables(engine)
    try:
        service = PedidoService(
            PedidoUnitOfWork(lambda: Session(engine, expire_on_commit=False))
        )
        with pytest.raises(DatosPedidoInvalidos):
            service.create_pedido(
                1,
                PedidoCreate(
                    items=[ItemPedidoCreate(producto_id=1, cantidad=1)],
                    forma_pago="EFECTIVO",
                    direccion_entrega="     ",
                ),
            )
    finally:
        engine.dispose()


def test_pedidos_sin_commit_en_repo_service_router() -> None:
    """Verifica estáticamente por AST que repository, service y router no llaman .commit()."""
    base_dir = Path(__file__).resolve().parents[1] / "app" / "modules" / "pedidos"
    for filename in ("repository.py", "service.py", "router.py"):
        tree = ast.parse((base_dir / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr != "commit", f"{filename} invoca .commit()"
