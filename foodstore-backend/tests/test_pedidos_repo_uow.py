"""Pruebas de integración para PedidoRepository y PedidoUnitOfWork (E3.3)."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session

from app.core.database import _build_engine, create_all_tables
from app.modules.categorias.models import Categoria
from app.modules.pedidos import (
    DetallePedido,
    Pedido,
    PedidoRead,
    PedidoRepository,
    PedidoUnitOfWork,
)
from app.modules.productos.models import Producto
from app.modules.usuarios.models import Usuario


@pytest.fixture()
def session_factory() -> Callable[[], Session]:
    """Crea un motor SQLite en memoria aislado con tablas creadas para cada test."""
    engine = _build_engine("sqlite:///:memory:")
    create_all_tables(engine)
    return lambda: Session(engine)


def _seed_usuario_y_productos(
    session_factory: Callable[[], Session],
) -> tuple[int, int, int, int]:
    """Inserta usuarios, categoría y productos base para los tests de pedidos."""
    with Session(session_factory().bind, expire_on_commit=False) as session:
        user_1 = Usuario(
            username="cliente1",
            full_name="Cliente Uno",
            email="cliente1@example.com",
            hashed_password="hash_cliente1",
        )
        user_2 = Usuario(
            username="cliente2",
            full_name="Cliente Dos",
            email="cliente2@example.com",
            hashed_password="hash_cliente2",
        )
        categoria = Categoria(nombre="Pizzas", descripcion="Artesanales")
        session.add(user_1)
        session.add(user_2)
        session.add(categoria)
        session.flush()
        assert user_1.id is not None
        assert user_2.id is not None
        assert categoria.id is not None

        prod_1 = Producto(
            categoria_id=categoria.id,
            nombre="Muzzarella",
            precio_base=5000.0,
            stock=10,
            disponible=True,
        )
        prod_2 = Producto(
            categoria_id=categoria.id,
            nombre="Napolitana",
            precio_base=6200.0,
            stock=5,
            disponible=True,
        )
        session.add(prod_1)
        session.add(prod_2)
        session.commit()
        assert prod_1.id is not None
        assert prod_2.id is not None
        return user_1.id, user_2.id, prod_1.id, prod_2.id


def test_pedido_uow_comparte_sesion_y_expire_on_commit_false(
    session_factory: Callable[[], Session],
) -> None:
    """Verifica que PedidoUnitOfWork comparte la misma Session y fija expire_on_commit=False."""
    with PedidoUnitOfWork(session_factory=session_factory) as uow:
        assert uow.session is not None
        assert uow.session.expire_on_commit is False
        assert isinstance(uow.pedidos, PedidoRepository)
        assert uow.pedidos.session is uow.session
        assert uow.productos.session is uow.session
        assert uow.pedidos.session is uow.productos.session


def test_pedido_repository_list_by_usuario_y_list_all_con_filtro_estado(
    session_factory: Callable[[], Session],
) -> None:
    """Verifica list_by_usuario, list_all, list_paginado, orden descendente y filtro estado."""
    user_1_id, user_2_id, prod_1_id, _ = _seed_usuario_y_productos(session_factory)
    base_time = datetime(2026, 11, 19, 10, 0, 0, tzinfo=timezone.utc)

    with PedidoUnitOfWork(session_factory=session_factory) as uow:
        p1 = uow.pedidos.add(
            Pedido(
                usuario_id=user_1_id,
                estado="PENDIENTE",
                forma_pago="EFECTIVO",
                direccion_entrega="Av. Siempre Viva 100",
                total=5000.0,
                created_at=base_time,
                updated_at=base_time,
            )
        )
        p2 = uow.pedidos.add(
            Pedido(
                usuario_id=user_1_id,
                estado="ENTREGADO",
                forma_pago="TRANSFERENCIA",
                direccion_entrega="Av. Siempre Viva 200",
                total=10000.0,
                created_at=base_time + timedelta(minutes=10),
                updated_at=base_time + timedelta(minutes=10),
            )
        )
        p3 = uow.pedidos.add(
            Pedido(
                usuario_id=user_1_id,
                estado="PENDIENTE",
                forma_pago="EFECTIVO",
                direccion_entrega="Av. Siempre Viva 300",
                total=15000.0,
                created_at=base_time + timedelta(minutes=20),
                updated_at=base_time + timedelta(minutes=20),
            )
        )
        p4 = uow.pedidos.add(
            Pedido(
                usuario_id=user_2_id,
                estado="EN_PREPARACION",
                forma_pago="EFECTIVO",
                direccion_entrega="Calle Falsa 456",
                total=6200.0,
                created_at=base_time + timedelta(minutes=30),
                updated_at=base_time + timedelta(minutes=30),
            )
        )
        assert p1.id is not None and p2.id is not None and p3.id is not None and p4.id is not None
        uow.pedidos.add_detalle(
            DetallePedido(
                pedido_id=p3.id,
                producto_id=prod_1_id,
                cantidad=3,
                nombre_producto="Muzzarella",
                precio_unitario=5000.0,
                subtotal=15000.0,
            )
        )
        p1_id, p2_id, p3_id, p4_id = p1.id, p2.id, p3.id, p4.id

    with PedidoUnitOfWork(session_factory=session_factory) as uow:
        items_u1, total_u1 = uow.pedidos.list_by_usuario(user_1_id, skip=0, limit=2)
        assert total_u1 == 3
        assert [p.id for p in items_u1] == [p3_id, p2_id]
        assert len(items_u1[0].items) == 1

        items_u1_pend, total_u1_pend = uow.pedidos.list_by_usuario(
            user_1_id,
            estado="PENDIENTE",
        )
        assert total_u1_pend == 2
        assert [p.id for p in items_u1_pend] == [p3_id, p1_id]

        items_all, total_all = uow.pedidos.list_all(skip=1, limit=2)
        assert total_all == 4
        assert [p.id for p in items_all] == [p3_id, p2_id]

        items_prep, total_prep = uow.pedidos.list_paginado(estado="EN_PREPARACION")
        assert total_prep == 1
        assert [p.id for p in items_prep] == [p4_id]


def test_pedido_repository_count_by_estado_y_metricas_resumen(
    session_factory: Callable[[], Session],
) -> None:
    """Verifica count_by_estado, count_estado, count_pedidos_hoy y sum_ingresos_entregados."""
    user_1_id, _, _, _ = _seed_usuario_y_productos(session_factory)
    hoy = datetime.now(timezone.utc).date()
    ahora_hoy = datetime.combine(hoy, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=12)
    ayer = ahora_hoy - timedelta(days=1)

    with PedidoUnitOfWork(session_factory=session_factory) as uow:
        # Caso sin pedidos: las 4 claves deben existir con 0 y sum_ingresos_entregados == 0.0
        assert uow.pedidos.count_by_estado() == {
            "PENDIENTE": 0,
            "EN_PREPARACION": 0,
            "ENTREGADO": 0,
            "CANCELADO": 0,
        }
        assert uow.pedidos.sum_ingresos_entregados() == 0.0

        uow.pedidos.add(
            Pedido(
                usuario_id=user_1_id,
                estado="PENDIENTE",
                forma_pago="EFECTIVO",
                direccion_entrega="Dirección 111",
                total=4000.0,
                created_at=ahora_hoy,
                updated_at=ahora_hoy,
            )
        )
        uow.pedidos.add(
            Pedido(
                usuario_id=user_1_id,
                estado="ENTREGADO",
                forma_pago="TRANSFERENCIA",
                direccion_entrega="Dirección 222",
                total=5500.0,
                created_at=ahora_hoy,
                updated_at=ahora_hoy,
            )
        )
        uow.pedidos.add(
            Pedido(
                usuario_id=user_1_id,
                estado="ENTREGADO",
                forma_pago="EFECTIVO",
                direccion_entrega="Dirección 333",
                total=2500.0,
                created_at=ayer,
                updated_at=ayer,
            )
        )

    with PedidoUnitOfWork(session_factory=session_factory) as uow:
        conteos = uow.pedidos.count_by_estado()
        assert conteos == {
            "PENDIENTE": 1,
            "EN_PREPARACION": 0,
            "ENTREGADO": 2,
            "CANCELADO": 0,
        }
        assert uow.pedidos.count_estado("PENDIENTE") == 1
        assert uow.pedidos.count_estado("CANCELADO") == 0
        assert uow.pedidos.count_pedidos_hoy(fecha_hoy=hoy) == 2
        assert uow.pedidos.sum_ingresos_entregados() == pytest.approx(8000.0)


def test_pedido_uow_model_validate_dentro_del_with_y_acceso_post_commit(
    session_factory: Callable[[], Session],
) -> None:
    """Verifica PedidoRead.model_validate dentro del bloque with y acceso tras el commit."""
    user_1_id, _, prod_1_id, _ = _seed_usuario_y_productos(session_factory)

    with PedidoUnitOfWork(session_factory=session_factory) as uow:
        pedido = uow.pedidos.add(
            Pedido(
                usuario_id=user_1_id,
                estado="PENDIENTE",
                forma_pago="TRANSFERENCIA",
                direccion_entrega="San Martín 1234",
                notas="Sin aceitunas",
                total=10000.0,
            )
        )
        assert pedido.id is not None
        uow.pedidos.add_detalle(
            DetallePedido(
                pedido_id=pedido.id,
                producto_id=prod_1_id,
                cantidad=2,
                nombre_producto="Muzzarella",
                precio_unitario=5000.0,
                subtotal=10000.0,
            )
        )
        cargado = uow.pedidos.get_by_id_with_items(pedido.id)
        assert cargado is not None
        dto = PedidoRead.model_validate(cargado)

    # Acceso post-commit sin DetachedInstanceError gracias a expire_on_commit=False
    assert cargado.id == dto.id
    assert cargado.total == 10000.0
    assert dto.estado == "PENDIENTE"
    assert len(dto.items) == 1
    assert dto.items[0].nombre_producto == "Muzzarella"
    assert dto.items[0].subtotal == 10000.0


def test_pedido_uow_rollback_atomico_pedido_detalle_y_stock_producto(
    session_factory: Callable[[], Session],
) -> None:
    """Descuenta stock y crea pedido/detalle; al fallar revierte todo atómicamente."""
    user_1_id, _, prod_1_id, _ = _seed_usuario_y_productos(session_factory)

    with pytest.raises(RuntimeError, match="Fallo al procesar segundo ítem"):
        with PedidoUnitOfWork(session_factory=session_factory) as uow:
            producto = uow.productos.get_by_id(prod_1_id)
            assert producto is not None
            assert producto.stock == 10

            producto.stock -= 3
            uow.productos.add(producto)

            pedido = uow.pedidos.add(
                Pedido(
                    usuario_id=user_1_id,
                    estado="PENDIENTE",
                    forma_pago="EFECTIVO",
                    direccion_entrega="Belgrano 500",
                    total=15000.0,
                )
            )
            assert pedido.id is not None
            uow.pedidos.add_detalle(
                DetallePedido(
                    pedido_id=pedido.id,
                    producto_id=prod_1_id,
                    cantidad=3,
                    nombre_producto=producto.nombre,
                    precio_unitario=producto.precio_base,
                    subtotal=15000.0,
                )
            )
            raise RuntimeError("Fallo al procesar segundo ítem")

    with PedidoUnitOfWork(session_factory=session_factory) as uow:
        producto_post = uow.productos.get_by_id(prod_1_id)
        assert producto_post is not None
        assert producto_post.stock == 10

        pedidos, total = uow.pedidos.list_all()
        assert pedidos == []
        assert total == 0
