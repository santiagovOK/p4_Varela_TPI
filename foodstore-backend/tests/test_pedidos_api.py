"""Pruebas unitarias y de integración HTTP para el módulo de pedidos (E6.1–E6.4)."""

import ast
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
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


def test_cambiar_estado_pedido_permisos_admin(
    pedidos_client: tuple[TestClient, object],
) -> None:
    """Verifica RBAC admin por cookie HttpOnly, 404 inexistente y 422 por estado fuera de Literal."""
    client, test_engine = pedidos_client
    cliente = _create_db_user(
        test_engine, username="cliente_e62", email="cliente_e62@test.com", role="user"
    )
    admin = _create_db_user(
        test_engine, username="admin_e62", email="admin_e62@test.com", role="admin"
    )
    admin_disabled = _create_db_user(
        test_engine,
        username="admin_dis_e62",
        email="admin_dis_e62@test.com",
        role="admin",
        disabled=True,
    )

    resp_anon = client.patch(
        "/api/v1/pedidos/1/estado",
        json={"estado": "EN_PREPARACION"},
    )
    assert resp_anon.status_code == 401

    token_admin = create_access_token(admin.username, role=admin.role)
    resp_bearer = client.patch(
        "/api/v1/pedidos/1/estado",
        json={"estado": "EN_PREPARACION"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert resp_bearer.status_code == 401

    resp_user = client.patch(
        "/api/v1/pedidos/1/estado",
        json={"estado": "EN_PREPARACION"},
        cookies=_auth_cookies(cliente),
    )
    assert resp_user.status_code == 403

    resp_disabled = client.patch(
        "/api/v1/pedidos/1/estado",
        json={"estado": "EN_PREPARACION"},
        cookies=_auth_cookies(admin_disabled),
    )
    assert resp_disabled.status_code == 400
    assert resp_disabled.json()["detail"] == "Cuenta de usuario desactivada"

    resp_not_found = client.patch(
        "/api/v1/pedidos/99999/estado",
        json={"estado": "EN_PREPARACION"},
        cookies=_auth_cookies(admin),
    )
    assert resp_not_found.status_code == 404

    resp_literal = client.patch(
        "/api/v1/pedidos/1/estado",
        json={"estado": "DESPACHADO"},
        cookies=_auth_cookies(admin),
    )
    assert resp_literal.status_code == 422


def test_cambiar_estado_transiciones_validas_hasta_entregado_sin_alterar_stock(
    pedidos_client: tuple[TestClient, object],
) -> None:
    """PENDIENTE -> EN_PREPARACION -> ENTREGADO actualiza estado sin alterar stock ni snapshots."""
    client, test_engine = pedidos_client
    cliente = _create_db_user(
        test_engine, username="cli_ok", email="cli_ok@test.com", role="user"
    )
    admin = _create_db_user(
        test_engine, username="adm_ok", email="adm_ok@test.com", role="admin"
    )
    cat = _create_db_categoria(test_engine, nombre="Principales")
    p1 = _create_db_producto(
        test_engine,
        nombre="Pizza Muzzarella",
        categoria_id=cat.id,  # type: ignore[arg-type]
        precio_base=5000.0,
        stock=10,
    )
    p2 = _create_db_producto(
        test_engine,
        nombre="Agua Mineral",
        categoria_id=cat.id,  # type: ignore[arg-type]
        precio_base=1200.0,
        stock=6,
    )

    creado = client.post(
        "/api/v1/pedidos",
        json={
            "items": [
                {"producto_id": p1.id, "cantidad": 3},
                {"producto_id": p2.id, "cantidad": 2},
            ],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Av. Colón 1234",
        },
        cookies=_auth_cookies(cliente),
    )
    assert creado.status_code == 201
    pedido_data = creado.json()
    pedido_id = pedido_data["id"]

    r_prep = client.patch(
        f"/api/v1/pedidos/{pedido_id}/estado",
        json={"estado": "EN_PREPARACION"},
        cookies=_auth_cookies(admin),
    )
    assert r_prep.status_code == 200
    body_prep = r_prep.json()
    assert body_prep["estado"] == "EN_PREPARACION"
    assert body_prep["total"] == pedido_data["total"]
    assert body_prep["items"] == pedido_data["items"]

    with Session(test_engine) as session:  # type: ignore[arg-type]
        p1_db = session.get(Producto, p1.id)
        p2_db = session.get(Producto, p2.id)
        assert p1_db is not None and p1_db.stock == 7
        assert p2_db is not None and p2_db.stock == 4

    r_ent = client.patch(
        f"/api/v1/pedidos/{pedido_id}/estado",
        json={"estado": "ENTREGADO"},
        cookies=_auth_cookies(admin),
    )
    assert r_ent.status_code == 200
    body_ent = r_ent.json()
    assert body_ent["estado"] == "ENTREGADO"
    assert body_ent["total"] == pedido_data["total"]
    assert body_ent["items"] == pedido_data["items"]

    with Session(test_engine) as session:  # type: ignore[arg-type]
        p1_db = session.get(Producto, p1.id)
        p2_db = session.get(Producto, p2.id)
        assert p1_db is not None and p1_db.stock == 7
        assert p2_db is not None and p2_db.stock == 4


def test_cambiar_estado_cancelacion_desde_pendiente_y_en_preparacion_restituye_stock_rn03(
    pedidos_client: tuple[TestClient, object],
) -> None:
    """Cancelar desde PENDIENTE o EN_PREPARACION restituye stock aun con baja lógica/no disponible."""
    client, test_engine = pedidos_client
    cliente = _create_db_user(
        test_engine, username="cli_can", email="cli_can@test.com", role="user"
    )
    admin = _create_db_user(
        test_engine, username="adm_can", email="adm_can@test.com", role="admin"
    )
    cat = _create_db_categoria(test_engine, nombre="Hamburguesas")
    p_baja = _create_db_producto(
        test_engine,
        nombre="Burger Clásica",
        categoria_id=cat.id,  # type: ignore[arg-type]
        precio_base=4500.0,
        stock=10,
    )
    p_no_disp = _create_db_producto(
        test_engine,
        nombre="Papas Cheddar",
        categoria_id=cat.id,  # type: ignore[arg-type]
        precio_base=2500.0,
        stock=8,
    )

    # Caso A: PENDIENTE -> CANCELADO
    creado_a = client.post(
        "/api/v1/pedidos",
        json={
            "items": [
                {"producto_id": p_baja.id, "cantidad": 2},
                {"producto_id": p_no_disp.id, "cantidad": 3},
            ],
            "forma_pago": "TRANSFERENCIA",
            "direccion_entrega": "Av. Hipólito Yrigoyen 500",
        },
        cookies=_auth_cookies(cliente),
    )
    assert creado_a.status_code == 201
    pedido_a_id = creado_a.json()["id"]

    cancel_a = client.patch(
        f"/api/v1/pedidos/{pedido_a_id}/estado",
        json={"estado": "CANCELADO"},
        cookies=_auth_cookies(admin),
    )
    assert cancel_a.status_code == 200
    assert cancel_a.json()["estado"] == "CANCELADO"

    with Session(test_engine) as session:  # type: ignore[arg-type]
        p_baja_db = session.get(Producto, p_baja.id)
        p_no_disp_db = session.get(Producto, p_no_disp.id)
        assert p_baja_db is not None and p_baja_db.stock == 10
        assert p_no_disp_db is not None and p_no_disp_db.stock == 8

    # Caso B: EN_PREPARACION -> CANCELADO tras baja lógica y disponible=False
    creado_b = client.post(
        "/api/v1/pedidos",
        json={
            "items": [
                {"producto_id": p_baja.id, "cantidad": 4},
                {"producto_id": p_no_disp.id, "cantidad": 5},
            ],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Av. Rafael Núñez 4200",
        },
        cookies=_auth_cookies(cliente),
    )
    assert creado_b.status_code == 201
    pedido_b_id = creado_b.json()["id"]

    prep_b = client.patch(
        f"/api/v1/pedidos/{pedido_b_id}/estado",
        json={"estado": "EN_PREPARACION"},
        cookies=_auth_cookies(admin),
    )
    assert prep_b.status_code == 200

    with Session(test_engine) as session:  # type: ignore[arg-type]
        prod_1 = session.get(Producto, p_baja.id)
        prod_2 = session.get(Producto, p_no_disp.id)
        assert prod_1 is not None and prod_2 is not None
        prod_1.activo = False
        prod_2.disponible = False
        session.add(prod_1)
        session.add(prod_2)
        session.commit()

    cancel_b = client.patch(
        f"/api/v1/pedidos/{pedido_b_id}/estado",
        json={"estado": "CANCELADO"},
        cookies=_auth_cookies(admin),
    )
    assert cancel_b.status_code == 200
    assert cancel_b.json()["estado"] == "CANCELADO"

    with Session(test_engine) as session:  # type: ignore[arg-type]
        p_baja_db = session.get(Producto, p_baja.id)
        p_no_disp_db = session.get(Producto, p_no_disp.id)
        assert p_baja_db is not None and p_baja_db.stock == 10
        assert p_no_disp_db is not None and p_no_disp_db.stock == 8


def test_cambiar_estado_transiciones_invalidas_y_terminales_rn02_no_duplican_restitucion(
    pedidos_client: tuple[TestClient, object],
) -> None:
    """Rechaza con 400 transiciones inválidas y cambios desde terminales sin duplicar restitución."""
    client, test_engine = pedidos_client
    cliente = _create_db_user(
        test_engine, username="cli_inv", email="cli_inv@test.com", role="user"
    )
    admin = _create_db_user(
        test_engine, username="adm_inv", email="adm_inv@test.com", role="admin"
    )
    cat = _create_db_categoria(test_engine, nombre="Bebidas")
    prod = _create_db_producto(
        test_engine,
        nombre="Gaseosa 500ml",
        categoria_id=cat.id,  # type: ignore[arg-type]
        precio_base=1800.0,
        stock=10,
    )

    # Pedido 1: probar inválidas desde PENDIENTE, EN_PREPARACION y terminal ENTREGADO
    p1 = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": prod.id, "cantidad": 2}],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Bv. San Juan 800",
        },
        cookies=_auth_cookies(cliente),
    )
    assert p1.status_code == 201
    p1_id = p1.json()["id"]

    for destino in ("ENTREGADO", "PENDIENTE"):
        resp = client.patch(
            f"/api/v1/pedidos/{p1_id}/estado",
            json={"estado": destino},
            cookies=_auth_cookies(admin),
        )
        assert resp.status_code == 400

    assert (
        client.patch(
            f"/api/v1/pedidos/{p1_id}/estado",
            json={"estado": "EN_PREPARACION"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 200
    )

    for destino in ("PENDIENTE", "EN_PREPARACION"):
        resp = client.patch(
            f"/api/v1/pedidos/{p1_id}/estado",
            json={"estado": destino},
            cookies=_auth_cookies(admin),
        )
        assert resp.status_code == 400

    assert (
        client.patch(
            f"/api/v1/pedidos/{p1_id}/estado",
            json={"estado": "ENTREGADO"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 200
    )

    for destino in ("CANCELADO", "PENDIENTE", "EN_PREPARACION", "ENTREGADO"):
        resp = client.patch(
            f"/api/v1/pedidos/{p1_id}/estado",
            json={"estado": destino},
            cookies=_auth_cookies(admin),
        )
        assert resp.status_code == 400

    with Session(test_engine) as session:  # type: ignore[arg-type]
        prod_db = session.get(Producto, prod.id)
        assert prod_db is not None and prod_db.stock == 8

    # Pedido 2: terminal CANCELADO no debe duplicar restitución de stock
    p2 = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": prod.id, "cantidad": 3}],
            "forma_pago": "TRANSFERENCIA",
            "direccion_entrega": "Av. Vélez Sarsfield 1000",
        },
        cookies=_auth_cookies(cliente),
    )
    assert p2.status_code == 201
    p2_id = p2.json()["id"]

    assert (
        client.patch(
            f"/api/v1/pedidos/{p2_id}/estado",
            json={"estado": "CANCELADO"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 200
    )

    for destino in ("CANCELADO", "PENDIENTE", "EN_PREPARACION", "ENTREGADO"):
        resp = client.patch(
            f"/api/v1/pedidos/{p2_id}/estado",
            json={"estado": destino},
            cookies=_auth_cookies(admin),
        )
        assert resp.status_code == 400

    with Session(test_engine) as session:  # type: ignore[arg-type]
        prod_db = session.get(Producto, prod.id)
        assert prod_db is not None and prod_db.stock == 8


def test_pedidos_sin_commit_en_repo_service_router() -> None:
    """Verifica estáticamente por AST que repository, service y router no llaman .commit()."""
    base_dir = Path(__file__).resolve().parents[1] / "app" / "modules" / "pedidos"
    for filename in ("repository.py", "service.py", "router.py"):
        tree = ast.parse((base_dir / filename).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr != "commit", f"{filename} invoca .commit()"


def test_listar_pedidos_permisos_paginacion_y_filtro_estado(
    pedidos_client: tuple[TestClient, object],
) -> None:
    """Lista pedidos propios para user, todos para admin, con paginación y filtro estado."""
    client, test_engine = pedidos_client
    cliente_a = _create_db_user(
        test_engine, username="cli_list_a", email="cli_list_a@test.com", role="user"
    )
    cliente_b = _create_db_user(
        test_engine, username="cli_list_b", email="cli_list_b@test.com", role="user"
    )
    admin = _create_db_user(
        test_engine, username="adm_list", email="adm_list@test.com", role="admin"
    )
    inactivo = _create_db_user(
        test_engine,
        username="cli_list_off",
        email="cli_list_off@test.com",
        role="user",
        disabled=True,
    )
    cat = _create_db_categoria(test_engine, nombre="Pizzas")
    prod = _create_db_producto(
        test_engine,
        nombre="Muzzarella",
        categoria_id=cat.id,  # type: ignore[arg-type]
        precio_base=5000.0,
        stock=20,
    )

    assert client.get("/api/v1/pedidos").status_code == 401
    token_a = create_access_token(cliente_a.username, role=cliente_a.role)
    assert (
        client.get(
            "/api/v1/pedidos",
            headers={"Authorization": f"Bearer {token_a}"},
        ).status_code
        == 401
    )
    resp_inactivo = client.get("/api/v1/pedidos", cookies=_auth_cookies(inactivo))
    assert resp_inactivo.status_code == 400
    assert resp_inactivo.json()["detail"] == "Cuenta de usuario desactivada"

    # Crear 2 pedidos para cliente_a y 1 para cliente_b
    p_a1 = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": prod.id, "cantidad": 1}],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Av. Colón 100",
        },
        cookies=_auth_cookies(cliente_a),
    )
    assert p_a1.status_code == 201
    p_a1_id = p_a1.json()["id"]

    p_b1 = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": prod.id, "cantidad": 2}],
            "forma_pago": "TRANSFERENCIA",
            "direccion_entrega": "Av. General Paz 200",
        },
        cookies=_auth_cookies(cliente_b),
    )
    assert p_b1.status_code == 201
    p_b1_id = p_b1.json()["id"]

    p_a2 = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": prod.id, "cantidad": 1}],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Av. Colón 300",
        },
        cookies=_auth_cookies(cliente_a),
    )
    assert p_a2.status_code == 201
    p_a2_id = p_a2.json()["id"]

    # Pasar p_a1 a EN_PREPARACION -> ENTREGADO
    assert (
        client.patch(
            f"/api/v1/pedidos/{p_a1_id}/estado",
            json={"estado": "EN_PREPARACION"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/pedidos/{p_a1_id}/estado",
            json={"estado": "ENTREGADO"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 200
    )

    # cliente_a solo ve sus 2 pedidos, ordenados descendentemente y con items hidratados
    list_a = client.get("/api/v1/pedidos", cookies=_auth_cookies(cliente_a))
    assert list_a.status_code == 200
    data_a = list_a.json()
    assert data_a["total"] == 2
    assert [item["id"] for item in data_a["items"]] == [p_a2_id, p_a1_id]
    assert len(data_a["items"][0]["items"]) == 1

    # cliente_b solo ve su pedido
    list_b = client.get("/api/v1/pedidos", cookies=_auth_cookies(cliente_b))
    assert list_b.status_code == 200
    assert list_b.json()["total"] == 1
    assert [item["id"] for item in list_b.json()["items"]] == [p_b1_id]

    # admin ve todos (3 pedidos)
    list_admin = client.get("/api/v1/pedidos", cookies=_auth_cookies(admin))
    assert list_admin.status_code == 200
    assert list_admin.json()["total"] == 3
    assert [item["id"] for item in list_admin.json()["items"]] == [
        p_a2_id,
        p_b1_id,
        p_a1_id,
    ]

    # Filtro por estado para user y admin
    filt_a_entregado = client.get(
        "/api/v1/pedidos?estado=ENTREGADO", cookies=_auth_cookies(cliente_a)
    )
    assert filt_a_entregado.status_code == 200
    assert filt_a_entregado.json()["total"] == 1
    assert filt_a_entregado.json()["items"][0]["id"] == p_a1_id

    filt_admin_pendiente = client.get(
        "/api/v1/pedidos?estado=PENDIENTE", cookies=_auth_cookies(admin)
    )
    assert filt_admin_pendiente.status_code == 200
    assert filt_admin_pendiente.json()["total"] == 2
    assert [item["id"] for item in filt_admin_pendiente.json()["items"]] == [
        p_a2_id,
        p_b1_id,
    ]

    # Paginación skip/limit y validación 422
    pag_admin = client.get(
        "/api/v1/pedidos?skip=1&limit=1", cookies=_auth_cookies(admin)
    )
    assert pag_admin.status_code == 200
    assert pag_admin.json()["total"] == 3
    assert [item["id"] for item in pag_admin.json()["items"]] == [p_b1_id]

    for bad_query in ("estado=INVALIDO", "skip=-1", "limit=0", "limit=101"):
        assert (
            client.get(
                f"/api/v1/pedidos?{bad_query}", cookies=_auth_cookies(admin)
            ).status_code
            == 422
        )


def test_obtener_pedido_detalle_dueno_admin_y_errores_403_404(
    pedidos_client: tuple[TestClient, object],
) -> None:
    """Valida GET /api/v1/pedidos/{id} para dueño, admin, pedido ajeno (403) e inexistente (404)."""
    client, test_engine = pedidos_client
    cliente_a = _create_db_user(
        test_engine, username="cli_det_a", email="cli_det_a@test.com", role="user"
    )
    cliente_b = _create_db_user(
        test_engine, username="cli_det_b", email="cli_det_b@test.com", role="user"
    )
    admin = _create_db_user(
        test_engine, username="adm_det", email="adm_det@test.com", role="admin"
    )
    inactivo = _create_db_user(
        test_engine,
        username="cli_det_off",
        email="cli_det_off@test.com",
        role="user",
        disabled=True,
    )
    cat = _create_db_categoria(test_engine, nombre="Empanadas")
    prod = _create_db_producto(
        test_engine,
        nombre="Empanada Salteña",
        categoria_id=cat.id,  # type: ignore[arg-type]
        precio_base=1200.0,
        stock=15,
    )

    creado = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": prod.id, "cantidad": 4}],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Av. Rafael Núñez 500",
        },
        cookies=_auth_cookies(cliente_a),
    )
    assert creado.status_code == 201
    pedido_id = creado.json()["id"]

    assert client.get(f"/api/v1/pedidos/{pedido_id}").status_code == 401
    assert (
        client.get(
            f"/api/v1/pedidos/{pedido_id}", cookies=_auth_cookies(inactivo)
        ).status_code
        == 400
    )

    # Dueño consulta su pedido
    resp_dueno = client.get(
        f"/api/v1/pedidos/{pedido_id}", cookies=_auth_cookies(cliente_a)
    )
    assert resp_dueno.status_code == 200
    assert resp_dueno.json()["id"] == pedido_id
    assert len(resp_dueno.json()["items"]) == 1
    assert resp_dueno.json()["items"][0]["nombre_producto"] == "Empanada Salteña"

    # Otro usuario intenta consultar pedido ajeno -> 403
    resp_ajeno = client.get(
        f"/api/v1/pedidos/{pedido_id}", cookies=_auth_cookies(cliente_b)
    )
    assert resp_ajeno.status_code == 403

    # Admin puede consultar cualquier pedido
    resp_admin = client.get(
        f"/api/v1/pedidos/{pedido_id}", cookies=_auth_cookies(admin)
    )
    assert resp_admin.status_code == 200
    assert resp_admin.json()["id"] == pedido_id

    # Pedido inexistente -> 404
    assert (
        client.get("/api/v1/pedidos/99999", cookies=_auth_cookies(cliente_a)).status_code
        == 404
    )
    assert (
        client.get("/api/v1/pedidos/99999", cookies=_auth_cookies(admin)).status_code
        == 404
    )


def test_cancelar_pedido_cliente_dueno_pendiente_restituye_stock_y_errores(
    pedidos_client: tuple[TestClient, object],
) -> None:
    """Valida PATCH /api/v1/pedidos/{id}/cancelar: solo dueño y solo en PENDIENTE."""
    client, test_engine = pedidos_client
    cliente_a = _create_db_user(
        test_engine, username="cli_can_a", email="cli_can_a@test.com", role="user"
    )
    cliente_b = _create_db_user(
        test_engine, username="cli_can_b", email="cli_can_b@test.com", role="user"
    )
    admin = _create_db_user(
        test_engine, username="adm_can", email="adm_can@test.com", role="admin"
    )
    inactivo = _create_db_user(
        test_engine,
        username="cli_can_off",
        email="cli_can_off@test.com",
        role="user",
        disabled=True,
    )
    cat = _create_db_categoria(test_engine, nombre="Sandwiches")
    prod = _create_db_producto(
        test_engine,
        nombre="Lomito Completo",
        categoria_id=cat.id,  # type: ignore[arg-type]
        precio_base=9000.0,
        stock=10,
    )

    p1 = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": prod.id, "cantidad": 3}],
            "forma_pago": "EFECTIVO",
            "direccion_entrega": "Av. Chacabuco 120",
        },
        cookies=_auth_cookies(cliente_a),
    )
    assert p1.status_code == 201
    p1_id = p1.json()["id"]

    assert client.patch(f"/api/v1/pedidos/{p1_id}/cancelar").status_code == 401
    assert (
        client.patch(
            f"/api/v1/pedidos/{p1_id}/cancelar", cookies=_auth_cookies(inactivo)
        ).status_code
        == 400
    )
    assert (
        client.patch(
            "/api/v1/pedidos/99999/cancelar", cookies=_auth_cookies(cliente_a)
        ).status_code
        == 404
    )

    # Otro usuario o admin (no dueño) no pueden cancelar por la ruta de dueño -> 403
    assert (
        client.patch(
            f"/api/v1/pedidos/{p1_id}/cancelar", cookies=_auth_cookies(cliente_b)
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/pedidos/{p1_id}/cancelar", cookies=_auth_cookies(admin)
        ).status_code
        == 403
    )

    # Marcar producto como no disponible y baja lógica tras la compra; aún debe restituir stock
    with Session(test_engine) as session:  # type: ignore[arg-type]
        prod_db = session.get(Producto, prod.id)
        assert prod_db is not None
        assert prod_db.stock == 7
        prod_db.activo = False
        prod_db.disponible = False
        session.add(prod_db)
        session.commit()

    cancel_ok = client.patch(
        f"/api/v1/pedidos/{p1_id}/cancelar", cookies=_auth_cookies(cliente_a)
    )
    assert cancel_ok.status_code == 200
    assert cancel_ok.json()["estado"] == "CANCELADO"

    with Session(test_engine) as session:  # type: ignore[arg-type]
        prod_db = session.get(Producto, prod.id)
        assert prod_db is not None and prod_db.stock == 10
        prod_db.activo = True
        prod_db.disponible = True
        session.add(prod_db)
        session.commit()

    # Reintentar cancelar un pedido ya CANCELADO -> 400 sin duplicar restitución
    assert (
        client.patch(
            f"/api/v1/pedidos/{p1_id}/cancelar", cookies=_auth_cookies(cliente_a)
        ).status_code
        == 400
    )
    with Session(test_engine) as session:  # type: ignore[arg-type]
        prod_db = session.get(Producto, prod.id)
        assert prod_db is not None and prod_db.stock == 10

    # Pedido en EN_PREPARACION o ENTREGADO tampoco puede cancelarse por esta vía -> 400
    p2 = client.post(
        "/api/v1/pedidos",
        json={
            "items": [{"producto_id": prod.id, "cantidad": 2}],
            "forma_pago": "TRANSFERENCIA",
            "direccion_entrega": "Av. Pueyrredón 450",
        },
        cookies=_auth_cookies(cliente_a),
    )
    assert p2.status_code == 201
    p2_id = p2.json()["id"]

    assert (
        client.patch(
            f"/api/v1/pedidos/{p2_id}/estado",
            json={"estado": "EN_PREPARACION"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/pedidos/{p2_id}/cancelar", cookies=_auth_cookies(cliente_a)
        ).status_code
        == 400
    )

    assert (
        client.patch(
            f"/api/v1/pedidos/{p2_id}/estado",
            json={"estado": "ENTREGADO"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/pedidos/{p2_id}/cancelar", cookies=_auth_cookies(cliente_a)
        ).status_code
        == 400
    )


def test_resumen_pedidos_admin_antes_de_id_y_metricas(
    pedidos_client: tuple[TestClient, object],
) -> None:
    """Valida GET /api/v1/pedidos/resumen: orden de ruta, permisos y métricas exactas."""
    client, test_engine = pedidos_client
    cliente = _create_db_user(
        test_engine, username="cli_res", email="cli_res@test.com", role="user"
    )
    admin = _create_db_user(
        test_engine, username="adm_res", email="adm_res@test.com", role="admin"
    )
    admin_off = _create_db_user(
        test_engine,
        username="adm_res_off",
        email="adm_res_off@test.com",
        role="admin",
        disabled=True,
    )

    # Verificar permisos y que no colisiona con /{id} (no retorna 422)
    assert client.get("/api/v1/pedidos/resumen").status_code == 401
    assert (
        client.get(
            "/api/v1/pedidos/resumen", cookies=_auth_cookies(cliente)
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/v1/pedidos/resumen", cookies=_auth_cookies(admin_off)
        ).status_code
        == 400
    )

    # Base vacía -> todo en 0
    vacio = client.get("/api/v1/pedidos/resumen", cookies=_auth_cookies(admin))
    assert vacio.status_code == 200
    assert vacio.json() == {
        "pendientes": 0,
        "en_preparacion": 0,
        "entregados": 0,
        "cancelados": 0,
        "pedidos_hoy": 0,
        "ingresos_entregados": 0.0,
    }

    cat = _create_db_categoria(test_engine, nombre="Pastas")
    prod = _create_db_producto(
        test_engine,
        nombre="Sorrentinos",
        categoria_id=cat.id,  # type: ignore[arg-type]
        precio_base=4500.0,
        stock=20,
    )

    # Crear 4 pedidos: 1 PENDIENTE (ayer), 1 EN_PREPARACION (hoy), 1 ENTREGADO (hoy), 1 CANCELADO (hoy)
    ids: list[int] = []
    for cantidad in (1, 2, 3, 1):
        resp = client.post(
            "/api/v1/pedidos",
            json={
                "items": [{"producto_id": prod.id, "cantidad": cantidad}],
                "forma_pago": "EFECTIVO",
                "direccion_entrega": "Av. Hipólito Yrigoyen 200",
            },
            cookies=_auth_cookies(cliente),
        )
        assert resp.status_code == 201
        ids.append(resp.json()["id"])

    p_pend_ayer, p_prep, p_entregado, p_cancelado = ids

    # Mover p_pend_ayer al día anterior para probar pedidos_hoy
    with Session(test_engine) as session:  # type: ignore[arg-type]
        pedido_ayer = session.get(Pedido, p_pend_ayer)
        assert pedido_ayer is not None
        pedido_ayer.created_at = datetime.now(timezone.utc) - timedelta(days=1)
        session.add(pedido_ayer)
        session.commit()

    assert (
        client.patch(
            f"/api/v1/pedidos/{p_prep}/estado",
            json={"estado": "EN_PREPARACION"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/pedidos/{p_entregado}/estado",
            json={"estado": "EN_PREPARACION"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/pedidos/{p_entregado}/estado",
            json={"estado": "ENTREGADO"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/v1/pedidos/{p_cancelado}/estado",
            json={"estado": "CANCELADO"},
            cookies=_auth_cookies(admin),
        ).status_code
        == 200
    )

    resumen = client.get("/api/v1/pedidos/resumen", cookies=_auth_cookies(admin))
    assert resumen.status_code == 200
    assert resumen.json() == {
        "pendientes": 1,
        "en_preparacion": 1,
        "entregados": 1,
        "cancelados": 1,
        "pedidos_hoy": 3,
        "ingresos_entregados": 13500.0,
    }
