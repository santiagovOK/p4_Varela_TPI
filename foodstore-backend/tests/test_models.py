"""Pruebas unitarias y de persistencia para los modelos UML Categoria y Producto (E2.1)."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, inspect

from app.core.database import _build_engine, create_all_tables
from app.modules.categorias.models import Categoria
from app.modules.categorias.schemas import CategoriaRead
from app.modules.productos.models import Producto
from app.modules.productos.schemas import ProductoRead


@pytest.fixture
def db_engine():
    """Crea un motor SQLite en memoria con esquema TPI limpio."""
    eng = _build_engine("sqlite:///:memory:")
    create_all_tables(eng)
    try:
        yield eng
    finally:
        eng.dispose()


def test_ddl_tablas_y_ausencia_artefactos_parcial(db_engine) -> None:
    """Verifica tablas UML `categorias` y `productos` sin artefactos del segundo parcial."""
    inspector = inspect(db_engine)
    tables = sorted(inspector.get_table_names())
    assert tables == ["categorias", "productos"]
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

    fks = inspector.get_foreign_keys("productos")
    assert len(fks) == 1
    assert fks[0]["referred_table"] == "categorias"
    assert fks[0]["constrained_columns"] == ["categoria_id"]

    # En E2.1 aún no se declaran detalles ni referencias a Pedido/DetallePedido.
    assert not hasattr(Producto, "detalles")
    assert "detalles" not in Producto.__sqlmodel_relationships__
    assert set(SQLModel.metadata.tables.keys()) == {"categorias", "productos"}


def test_persistencia_relacion_1_n_y_model_validate(db_engine) -> None:
    """Verifica relación 1:N Categoria-Producto y model_validate con expire_on_commit=False."""
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
        session.commit()

        assert categoria.id is not None
        assert categoria.activo is True
        assert producto.id is not None
        assert producto.activo is True
        assert producto.categoria is categoria
        assert categoria.productos == [producto]

        cat_dto = CategoriaRead.model_validate(categoria)
        prod_dto = ProductoRead.model_validate(producto)

        assert cat_dto.nombre == "Hamburguesas"
        assert prod_dto.nombre == "Clásica Doble"
        assert prod_dto.stock == 15
        assert prod_dto.categoria.id == categoria.id
        assert prod_dto.categoria.nombre == "Hamburguesas"


def test_integridad_nombre_unico_y_fk_categoria(db_engine) -> None:
    """Verifica restricción UNIQUE en Categoria.nombre y FK obligatoria en Producto."""
    with Session(db_engine, expire_on_commit=False) as session:
        session.add(Categoria(nombre="Bebidas"))
        session.commit()

    with Session(db_engine, expire_on_commit=False) as session:
        session.add(Categoria(nombre="Bebidas"))
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
