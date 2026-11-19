"""Pruebas unitarias y de persistencia para las 5 entidades UML del TPI (E2.1 + E2.2)."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, inspect

from app.core.database import _build_engine, create_all_tables
from app.modules.categorias.models import Categoria
from app.modules.categorias.schemas import CategoriaRead
from app.modules.pedidos.models import DetallePedido, Pedido
from app.modules.pedidos.schemas import DetallePedidoRead, PedidoRead
from app.modules.productos.models import Producto
from app.modules.productos.schemas import ProductoRead
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import UserPublic


@pytest.fixture
def db_engine():
    """Crea un motor SQLite en memoria con esquema TPI limpio."""
    eng = _build_engine("sqlite:///:memory:")
    create_all_tables(eng)
    try:
        yield eng
    finally:
        eng.dispose()


def test_ddl_cinco_tablas_uml_y_ausencia_artefactos_parcial(db_engine) -> None:
    """Verifica las 5 tablas UML, columnas, FKs y ausencia de artefactos del parcial."""
    inspector = inspect(db_engine)
    tables = sorted(inspector.get_table_names())
    assert tables == ["categorias", "detalle_pedidos", "pedidos", "productos", "usuarios"]
    assert set(SQLModel.metadata.tables.keys()) == {
        "categorias",
        "detalle_pedidos",
        "pedidos",
        "productos",
        "usuarios",
    }
    assert "unidades_medida" not in tables
    assert "productos_categorias" not in tables

    cat_cols = {col["name"]: col for col in inspector.get_columns("categorias")}
    assert set(cat_cols.keys()) == {"id", "nombre", "descripcion", "activo"}
    assert cat_cols["nombre"]["nullable"] is False
    assert cat_cols["descripcion"]["nullable"] is True
    assert cat_cols["activo"]["nullable"] is False

    prod_cols = {col["name"]: col for col in inspector.get_columns("productos")}
    assert set(prod_cols.keys()) == {
        "id",
        "categoria_id",
        "nombre",
        "descripcion",
        "precio_base",
        "imagen_url",
        "stock",
        "disponible",
        "activo",
    }
    for obsolete_col in ("unidad_venta_id", "stock_cantidad", "hay_stock", "anulado_at"):
        assert obsolete_col not in prod_cols

    prod_fks = inspector.get_foreign_keys("productos")
    assert len(prod_fks) == 1
    assert prod_fks[0]["referred_table"] == "categorias"
    assert prod_fks[0]["constrained_columns"] == ["categoria_id"]

    user_cols = {col["name"]: col for col in inspector.get_columns("usuarios")}
    assert set(user_cols.keys()) == {
        "id",
        "username",
        "full_name",
        "email",
        "hashed_password",
        "role",
        "disabled",
        "created_at",
    }
    assert user_cols["username"]["nullable"] is False
    assert user_cols["email"]["nullable"] is False
    assert user_cols["hashed_password"]["nullable"] is False
    assert user_cols["created_at"]["nullable"] is False

    ped_cols = {col["name"]: col for col in inspector.get_columns("pedidos")}
    assert set(ped_cols.keys()) == {
        "id",
        "usuario_id",
        "estado",
        "forma_pago",
        "direccion_entrega",
        "notas",
        "total",
        "created_at",
        "updated_at",
    }
    assert ped_cols["notas"]["nullable"] is True
    assert ped_cols["direccion_entrega"]["nullable"] is False
    ped_fks = inspector.get_foreign_keys("pedidos")
    assert len(ped_fks) == 1
    assert ped_fks[0]["referred_table"] == "usuarios"
    assert ped_fks[0]["constrained_columns"] == ["usuario_id"]

    det_cols = {col["name"]: col for col in inspector.get_columns("detalle_pedidos")}
    assert set(det_cols.keys()) == {
        "id",
        "pedido_id",
        "producto_id",
        "cantidad",
        "nombre_producto",
        "precio_unitario",
        "subtotal",
    }
    det_fks = {
        tuple(fk["constrained_columns"]): fk["referred_table"]
        for fk in inspector.get_foreign_keys("detalle_pedidos")
    }
    assert det_fks == {
        ("pedido_id",): "pedidos",
        ("producto_id",): "productos",
    }

    # Verifica declaración de relaciones UML en Producto.
    assert "detalles" in Producto.__sqlmodel_relationships__


def test_persistencia_relaciones_bidireccionales_y_snapshots(db_engine) -> None:
    """Verifica relaciones bidireccionales UML, snapshots y model_validate."""
    with Session(db_engine, expire_on_commit=False) as session:
        categoria = Categoria(nombre="Hamburguesas", descripcion="A la parrilla")
        session.add(categoria)
        session.flush()

        producto = Producto(
            categoria_id=categoria.id,
            nombre="Clásica Doble",
            descripcion="Doble carne y cheddar",
            precio_base=9500.0,
            imagen_url="https://example.com/clasica.jpg",
            stock=15,
            disponible=True,
        )
        session.add(producto)

        usuario = Usuario(
            username="cliente1",
            full_name="Cliente Uno",
            email="cliente1@example.com",
            hashed_password="$2b$12$fakehashedpasswordvalue1234567890",
        )
        session.add(usuario)
        session.flush()

        pedido = Pedido(
            usuario_id=usuario.id,
            forma_pago="EFECTIVO",
            direccion_entrega="Av. Siempre Viva 742",
            notas="Sin cebolla",
            total=19000.0,
        )
        session.add(pedido)
        session.flush()

        detalle = DetallePedido(
            pedido_id=pedido.id,
            producto_id=producto.id,
            cantidad=2,
            nombre_producto=producto.nombre,
            precio_unitario=producto.precio_base,
            subtotal=19000.0,
        )
        session.add(detalle)
        session.commit()

        assert categoria.activo is True
        assert producto.activo is True
        assert usuario.role == "user"
        assert usuario.disabled is False
        assert usuario.created_at is not None
        assert pedido.estado == "PENDIENTE"
        assert pedido.created_at is not None
        assert pedido.updated_at is not None

        # Relaciones bidireccionales
        assert producto.categoria is categoria
        assert categoria.productos == [producto]
        assert pedido.usuario is usuario
        assert usuario.pedidos == [pedido]
        assert detalle.pedido is pedido
        assert pedido.items == [detalle]
        assert detalle.producto is producto
        assert producto.detalles == [detalle]

        # Validación de DTOs con expire_on_commit=False
        cat_dto = CategoriaRead.model_validate(categoria)
        prod_dto = ProductoRead.model_validate(producto)
        user_dto = UserPublic.model_validate(usuario)
        det_dto = DetallePedidoRead.model_validate(detalle)
        ped_dto = PedidoRead.model_validate(pedido)

        assert cat_dto.nombre == "Hamburguesas"
        assert prod_dto.categoria.nombre == "Hamburguesas"
        assert user_dto.username == "cliente1"
        assert not hasattr(user_dto, "hashed_password")
        assert det_dto.nombre_producto == "Clásica Doble"
        assert det_dto.precio_unitario == 9500.0
        assert det_dto.subtotal == 19000.0
        assert ped_dto.estado == "PENDIENTE"
        assert len(ped_dto.items) == 1
        assert ped_dto.items[0].nombre_producto == "Clásica Doble"

        # El snapshot en DetallePedido permanece inmutable aunque cambie el Producto.
        producto.nombre = "Clásica Doble Reformulada"
        producto.precio_base = 11000.0
        session.add(producto)
        session.commit()
        session.refresh(detalle)
        assert detalle.nombre_producto == "Clásica Doble"
        assert detalle.precio_unitario == 9500.0
        assert detalle.subtotal == 19000.0


def test_integridad_unicidad_y_foreign_keys(db_engine) -> None:
    """Verifica UNIQUE en Categoria/Usuario y FKs obligatorias en Producto/Pedido/Detalle."""
    with Session(db_engine, expire_on_commit=False) as session:
        session.add(Categoria(nombre="Bebidas"))
        session.add(
            Usuario(
                username="ana",
                full_name="Ana Pérez",
                email="ana@example.com",
                hashed_password="hash",
            )
        )
        session.commit()

    with Session(db_engine, expire_on_commit=False) as session:
        session.add(Categoria(nombre="Bebidas"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    with Session(db_engine, expire_on_commit=False) as session:
        session.add(
            Usuario(
                username="ana",
                full_name="Otra Ana",
                email="otra@example.com",
                hashed_password="hash",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    with Session(db_engine, expire_on_commit=False) as session:
        session.add(
            Usuario(
                username="ana2",
                full_name="Otra Ana",
                email="ana@example.com",
                hashed_password="hash",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    with Session(db_engine, expire_on_commit=False) as session:
        session.add(
            Producto(
                categoria_id=9999,
                nombre="Agua Mineral",
                precio_base=1500.0,
                stock=10,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    with Session(db_engine, expire_on_commit=False) as session:
        session.add(
            Pedido(
                usuario_id=9999,
                forma_pago="EFECTIVO",
                direccion_entrega="Calle Falsa 123",
                total=1000.0,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    with Session(db_engine, expire_on_commit=False) as session:
        session.add(
            DetallePedido(
                pedido_id=9999,
                producto_id=9999,
                cantidad=1,
                nombre_producto="Inexistente",
                precio_unitario=1000.0,
                subtotal=1000.0,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
