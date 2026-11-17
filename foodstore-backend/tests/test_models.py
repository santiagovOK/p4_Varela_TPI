"""Pruebas transaccionales de modelos relacionales SQLModel sobre PostgreSQL en esquema aislado."""

import os
import uuid
from decimal import Decimal
from typing import Generator

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, create_engine, inspect, text

import app.core.database as db
from app.modules.categorias.model import Categoria
from app.modules.productos.model import Producto, ProductoCategoria
from app.modules.unidades_medida.model import TipoUnidad, UnidadMedida

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
if not TEST_DATABASE_URL or not ("postgres" in TEST_DATABASE_URL):
    pytest.skip(
        "TEST_DATABASE_URL / DATABASE_URL no configurada para PostgreSQL; omitiendo pruebas sobre PostgreSQL",
        allow_module_level=True,
    )
else:
    try:
        _probe = create_engine(TEST_DATABASE_URL, echo=False)
        with _probe.connect() as _conn:
            _conn.execute(text("SELECT 1"))
        _probe.dispose()
    except Exception as _exc:
        pytest.skip(
            f"Servidor PostgreSQL no accesible ({_exc}); omitiendo pruebas sobre PostgreSQL",
            allow_module_level=True,
        )


@pytest.fixture(scope="function")
def pg_connection(monkeypatch) -> Generator:
    """Fixture transaccional que crea un esquema aislado con UUID y revierte toda mutación."""
    schema_name = f"e13_{uuid.uuid4().hex}"
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    connection = engine.connect()
    trans = connection.begin()

    try:
        connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
        connection.execute(text(f'SET LOCAL search_path TO "{schema_name}"'))

        monkeypatch.setattr(db, "engine", connection)
        db.create_db_and_tables()

        yield connection
    finally:
        trans.rollback()
        connection.close()
        engine.dispose()


# Consigna: docs/consignas_examen_2.md, 3.1, 4/R1 y 4/R3 — inspección DDL de tablas, tipos y claves foráneas.
def test_schema_ddl_inspection(pg_connection):
    """Verifica que existan exactamente las 4 tablas con sus PKs, FKs y precisiones numéricas."""
    inspector = inspect(pg_connection)
    tables = sorted(inspector.get_table_names())
    assert tables == ["categorias", "productos", "productos_categorias", "unidades_medida"]

    # Clave primaria compuesta en productos_categorias
    pk_pc = inspector.get_pk_constraint("productos_categorias").get("constrained_columns", [])
    assert sorted(pk_pc) == ["categoria_id", "producto_id"]

    # Claves foráneas (1 en productos, 2 en productos_categorias)
    fks_prod = inspector.get_foreign_keys("productos")
    assert len(fks_prod) == 1
    assert fks_prod[0]["referred_table"] == "unidades_medida"
    assert fks_prod[0]["constrained_columns"] == ["unidad_venta_id"]

    fks_pc = inspector.get_foreign_keys("productos_categorias")
    assert len(fks_pc) == 2
    referred = {fk["referred_table"] for fk in fks_pc}
    assert referred == {"productos", "categorias"}

    # Precisiones numéricas en productos (Numeric 18,2 y Numeric 18,3)
    cols = {col["name"]: col for col in inspector.get_columns("productos")}
    assert cols["precio_base"]["type"].precision == 18
    assert cols["precio_base"]["type"].scale == 2
    assert cols["stock_cantidad"]["type"].precision == 18
    assert cols["stock_cantidad"]["type"].scale == 3


# Consigna: docs/consignas_examen_2.md, 3.1, 4/R1 y 4/R3 — persistencia y navegación relacional 1:N y N:N.
def test_persistencia_y_navegacion_relacional(pg_connection):
    """Verifica persistencia de valores exactos y navegación bidireccional en 1:N y N:N."""
    with Session(bind=pg_connection) as session:
        unidad = UnidadMedida(
            nombre="kilogramo",
            simbolo="kg",
            tipo=TipoUnidad.peso,
        )
        session.add(unidad)
        session.flush()

        cat1 = Categoria(nombre="Almacén Seco")
        cat2 = Categoria(nombre="Productos Frescos")
        session.add_all([cat1, cat2])
        session.flush()

        producto = Producto(
            unidad_venta_id=unidad.id,
            nombre="Arroz Parboil",
            precio_base=Decimal("12.50"),
            stock_cantidad=Decimal("3.125"),
        )
        session.add(producto)
        session.flush()

        pc1 = ProductoCategoria(
            producto_id=producto.id,
            categoria_id=cat1.id,
            es_principal=True,
        )
        pc2 = ProductoCategoria(
            producto_id=producto.id,
            categoria_id=cat2.id,
            es_principal=False,
        )
        session.add_all([pc1, pc2])
        session.flush()

    # Reabrir sesión y navegar en ambos sentidos
    with Session(bind=pg_connection) as session:
        prod = session.get(Producto, producto.id)
        assert prod is not None
        assert prod.precio_base == Decimal("12.50")
        assert prod.stock_cantidad == Decimal("3.125")
        assert prod.unidad_venta.nombre == "kilogramo"
        assert {c.nombre for c in prod.categorias} == {"Almacén Seco", "Productos Frescos"}

        u = session.get(UnidadMedida, unidad.id)
        assert len(u.productos) == 1
        assert u.productos[0].nombre == "Arroz Parboil"

        c = session.get(Categoria, cat1.id)
        assert len(c.productos) == 1
        assert c.productos[0].nombre == "Arroz Parboil"


# Consigna: docs/consignas_examen_2.md, 3.1, 4/R3, RN-03, RN-07, RN-09 — restricciones de FK, duplicados y principal única.
def test_restricciones_relacionales_fks_y_asociacion(pg_connection):
    """Verifica rechazo de FKs inválidas, vínculos duplicados y restricción de categoría principal única."""
    with Session(bind=pg_connection) as session:
        unidad = UnidadMedida(nombre="pieza", simbolo="u", tipo=TipoUnidad.contable)
        session.add(unidad)
        session.flush()

        # FK inexistente en unidad_venta_id
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                prod_invalido = Producto(
                    unidad_venta_id=9999,
                    nombre="Producto Inexistente",
                    precio_base=Decimal("10.00"),
                )
                session.add(prod_invalido)
                session.flush()

        prod = Producto(
            unidad_venta_id=unidad.id,
            nombre="Alfajor Simple",
            precio_base=Decimal("5.00"),
        )
        session.add(prod)
        cat_a = Categoria(nombre="Golosinas")
        cat_b = Categoria(nombre="Snacks")
        session.add_all([cat_a, cat_b])
        session.flush()

        # Vínculo principal
        pc_a = ProductoCategoria(producto_id=prod.id, categoria_id=cat_a.id, es_principal=True)
        session.add(pc_a)
        session.flush()

        # Rechazar segundo vínculo principal para el mismo producto (RN-09 a nivel BD)
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                pc_b_invalido = ProductoCategoria(
                    producto_id=prod.id,
                    categoria_id=cat_b.id,
                    es_principal=True,
                )
                session.add(pc_b_invalido)
                session.flush()

        # Rechazar vínculo duplicado (misma PK producto_id + categoria_id) (RN-07)
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                pc_dup = ProductoCategoria(
                    producto_id=prod.id,
                    categoria_id=cat_a.id,
                    es_principal=False,
                )
                session.add(pc_dup)
                session.flush()

        # Permitir cambiar principal desmarcando la anterior primero
        pc_a.es_principal = False
        session.flush()
        pc_b = ProductoCategoria(producto_id=prod.id, categoria_id=cat_b.id, es_principal=True)
        session.add(pc_b)
        session.flush()
        assert pc_b.es_principal is True


# Consigna: docs/consignas_examen_2.md, 3.1 y 3.4/RN-02 — unicidad de nombre/símbolo y reutilización tras baja lógica.
def test_restricciones_unicidad_y_reutilizacion_nombre(pg_connection):
    """Verifica unicidad de UnidadMedida y unicidad parcial sobre activo = true para Producto y Categoria."""
    with Session(bind=pg_connection) as session:
        u1 = UnidadMedida(nombre="litro", simbolo="L", tipo=TipoUnidad.volumen)
        session.add(u1)
        session.flush()

        # Rechazar nombre duplicado en UnidadMedida
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                u_dup_nombre = UnidadMedida(nombre="litro", simbolo="lt", tipo=TipoUnidad.volumen)
                session.add(u_dup_nombre)
                session.flush()

        # Rechazar símbolo duplicado en UnidadMedida
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                u_dup_simbolo = UnidadMedida(nombre="litro extra", simbolo="L", tipo=TipoUnidad.volumen)
                session.add(u_dup_simbolo)
                session.flush()

        # Categoria: nombre único entre activas
        c1 = Categoria(nombre="Bebidas", activo=True)
        session.add(c1)
        session.flush()

        with pytest.raises(IntegrityError):
            with session.begin_nested():
                c2 = Categoria(nombre="Bebidas", activo=True)
                session.add(c2)
                session.flush()

        # Anulación lógica de c1 libera el nombre para una nueva categoría activa
        c1.activo = False
        session.flush()

        c3 = Categoria(nombre="Bebidas", activo=True)
        session.add(c3)
        session.flush()
        assert c3.id is not None

        # Producto: nombre único entre activos
        p1 = Producto(
            unidad_venta_id=u1.id,
            nombre="Agua Mineral",
            precio_base=Decimal("1.50"),
            activo=True,
        )
        session.add(p1)
        session.flush()

        with pytest.raises(IntegrityError):
            with session.begin_nested():
                p2 = Producto(
                    unidad_venta_id=u1.id,
                    nombre="Agua Mineral",
                    precio_base=Decimal("2.00"),
                    activo=True,
                )
                session.add(p2)
                session.flush()

        # Anulación lógica de p1 libera el nombre
        p1.activo = False
        session.flush()

        p3 = Producto(
            unidad_venta_id=u1.id,
            nombre="Agua Mineral",
            precio_base=Decimal("2.50"),
            activo=True,
        )
        session.add(p3)
        session.flush()
        assert p3.id is not None


# Consigna: docs/consignas_examen_2.md, 3.1 y 3.4/RN-01 — Check constraints a nivel de motor de base de datos.
def test_restricciones_check_constraints_insert_directo(pg_connection):
    """Verifica que la base de datos rechace violaciones a CheckConstraint mediante INSERT directo."""
    # Unidad de venta para inserciones
    pg_connection.execute(
        text("INSERT INTO unidades_medida (nombre, simbolo, tipo) VALUES ('metro', 'm', 'contable')")
    )
    res = pg_connection.execute(text("SELECT id FROM unidades_medida WHERE simbolo = 'm'"))
    unidad_id = res.scalar()

    # ck_productos_precio_base_no_negativo
    with pytest.raises(IntegrityError):
        with pg_connection.begin_nested():
            pg_connection.execute(
                text(
                    f"INSERT INTO productos (unidad_venta_id, nombre, precio_base, stock_cantidad, disponible, activo) "
                    f"VALUES ({unidad_id}, 'Cable', -5.00, 10, true, true)"
                )
            )

    # ck_productos_stock_cantidad_no_negativo
    with pytest.raises(IntegrityError):
        with pg_connection.begin_nested():
            pg_connection.execute(
                text(
                    f"INSERT INTO productos (unidad_venta_id, nombre, precio_base, stock_cantidad, disponible, activo) "
                    f"VALUES ({unidad_id}, 'Cable', 5.00, -1, true, true)"
                )
            )

    # ck_productos_nombre_min_length (< 3 chars)
    with pytest.raises(IntegrityError):
        with pg_connection.begin_nested():
            pg_connection.execute(
                text(
                    f"INSERT INTO productos (unidad_venta_id, nombre, precio_base, stock_cantidad, disponible, activo) "
                    f"VALUES ({unidad_id}, 'AB', 5.00, 10, true, true)"
                )
            )

    # ck_categorias_nombre_min_length (< 3 chars)
    with pytest.raises(IntegrityError):
        with pg_connection.begin_nested():
            pg_connection.execute(
                text("INSERT INTO categorias (nombre, activo) VALUES ('X', true)")
            )

    # TipoUnidad enum constraint (valor fuera de peso/volumen/contable)
    with pytest.raises(IntegrityError):
        with pg_connection.begin_nested():
            pg_connection.execute(
                text("INSERT INTO unidades_medida (nombre, simbolo, tipo) VALUES ('otra', 'ot', 'invalido')")
            )


# Consigna: docs/consignas_examen_2.md, 3.3 y 3.4/RN-11, RN-12 — independencia de estados y ausencia de columna hay_stock.
def test_independencia_estados_y_ausencia_hay_stock(pg_connection):
    """Verifica que disponible y activo sean independientes y que hay_stock no exista como columna persistida."""
    # Verificar a nivel metadatos que hay_stock no existe en la tabla
    assert not hasattr(Producto, "hay_stock")
    assert "hay_stock" not in Producto.__table__.columns

    with Session(bind=pg_connection) as session:
        u = UnidadMedida(nombre="gramo", simbolo="g", tipo=TipoUnidad.peso)
        session.add(u)
        session.flush()

        p = Producto(
            unidad_venta_id=u.id,
            nombre="Levadura",
            precio_base=Decimal("0.50"),
            stock_cantidad=Decimal("100.000"),
            disponible=True,
            activo=True,
        )
        session.add(p)
        session.flush()

        # Cambiar disponible preserva activo y stock
        p.disponible = False
        session.flush()
        assert p.disponible is False
        assert p.activo is True
        assert p.stock_cantidad == Decimal("100.000")

        # Cambiar activo preserva disponible y stock
        p.activo = False
        session.flush()
        assert p.activo is False
        assert p.disponible is False
        assert p.stock_cantidad == Decimal("100.000")
