"""Pruebas automatizadas para el servicio de categorías: reglas RN-02, RN-03, RN-04, RN-05, RN-06 y filtros 4/R3."""

import os
import uuid
from decimal import Decimal
from typing import Generator

import pytest
from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, text

# Consigna: docs/consignas_examen_2.md, 3.1 y 4/R3 — Registrar modelos para creación de tablas en SQLite o PostgreSQL.
import app.modules.categorias.model
import app.modules.productos.model
import app.modules.unidades_medida.model
from app.modules.categorias.model import Categoria
from app.modules.categorias.schema import CategoriaCreate, CategoriaUpdate
from app.modules.categorias.service import (
    actualizar_categoria,
    anular_categoria,
    crear_categoria,
    listar_categorias,
    obtener_categoria,
)
from app.modules.productos.model import Producto, ProductoCategoria
from app.modules.unidades_medida.model import TipoUnidad, UnidadMedida


def _resolve_test_engine():
    """Retorna un motor PostgreSQL si está accesible o SQLite in-memory como fallback determinista."""
    test_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if test_url and ("postgres" in test_url):
        try:
            probe = create_engine(test_url, echo=False)
            with probe.connect() as conn:
                conn.execute(text("SELECT 1"))
            probe.dispose()
            return test_url, True
        except Exception:
            pass
    return "sqlite:///:memory:", False


@pytest.fixture(scope="function")
def session_fixture() -> Generator[Session, None, None]:
    """Crea una sesión transaccional aislada para pruebas del servicio de categorías."""
    url, is_pg = _resolve_test_engine()

    if is_pg:
        schema_name = f"e22_{uuid.uuid4().hex}"
        admin_engine = create_engine(url, echo=False)
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
            conn.commit()

        engine = create_engine(
            url,
            connect_args={"options": f"-csearch_path={schema_name}"},
            echo=False,
        )
        SQLModel.metadata.create_all(
            engine,
            tables=[
                UnidadMedida.__table__,
                Categoria.__table__,
                Producto.__table__,
                ProductoCategoria.__table__,
            ],
        )

        with Session(engine) as session:
            yield session

        engine.dispose()
        with admin_engine.connect() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
            conn.commit()
        admin_engine.dispose()
    else:
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        @event.listens_for(engine, "connect")
        def _sqlite_char_length(dbapi_conn, _record):
            if hasattr(dbapi_conn, "create_function"):
                dbapi_conn.create_function("char_length", 1, len)

        SQLModel.metadata.create_all(
            engine,
            tables=[
                UnidadMedida.__table__,
                Categoria.__table__,
                Producto.__table__,
                ProductoCategoria.__table__,
            ],
        )
        with Session(engine) as session:
            yield session
        engine.dispose()


# Consigna: docs/consignas_examen_2.md, 3.4/RN-01, RN-03 y 4/R3 — Alta y recuperación de categoría activa.
def test_crear_y_obtener_categoria(session_fixture: Session):
    """Verifica la persistencia de una categoría activa con defaults y su consulta por ID."""
    dto = CategoriaCreate(
        nombre="Lácteos",
        descripcion="Productos refrigerados y derivados de leche",
    )
    categoria = crear_categoria(session_fixture, dto)

    assert categoria.id is not None
    assert categoria.nombre == "Lácteos"
    assert categoria.descripcion == "Productos refrigerados y derivados de leche"
    assert categoria.activo is True
    assert categoria.anulado_at is None

    recuperada = obtener_categoria(session_fixture, categoria.id)
    assert recuperada.id == categoria.id
    assert recuperada.nombre == "Lácteos"
    assert recuperada.activo is True


# Consigna: docs/consignas_examen_2.md, 3.4/RN-02 y RN-13 — Unicidad de nombre entre activas con 409 y fail-fast.
def test_crear_categoria_nombre_duplicado_activo_lanza_409_rn02(session_fixture: Session):
    """Verifica que intentar crear una categoría con nombre repetido entre activas lance 409."""
    dto1 = CategoriaCreate(nombre="Bebidas", descripcion="Aguas y jugos")
    c1 = crear_categoria(session_fixture, dto1)
    assert c1.id is not None

    dto_duplicado = CategoriaCreate(nombre="Bebidas", descripcion="Otra descripción")
    with pytest.raises(HTTPException) as exc_info:
        crear_categoria(session_fixture, dto_duplicado)

    assert exc_info.value.status_code == 409
    assert "Ya existe una categoría activa con el nombre 'Bebidas'." in exc_info.value.detail

    # RN-13: Verificar que no se insertó un segundo registro
    todas = listar_categorias(session_fixture)
    assert len(todas) == 1
    assert todas[0].id == c1.id


# Consigna: docs/consignas_examen_2.md, 3.4/RN-02 y RN-04 — Anulación lógica y liberación de nombre para nueva alta.
def test_anular_categoria_libera_nombre_para_nueva_alta_rn02_rn04(session_fixture: Session):
    """Verifica que la anulación lógica libere el nombre permitiendo dar de alta una nueva categoría activa."""
    c1 = crear_categoria(
        session_fixture,
        CategoriaCreate(nombre="Golosinas", descripcion="Caramelos y chocolates"),
    )
    cat_id1 = c1.id
    assert cat_id1 is not None

    anular_categoria(session_fixture, cat_id1)
    session_fixture.refresh(c1)

    assert c1.activo is False
    assert c1.anulado_at is not None

    # RN-02: Nombre liberado, permite nueva alta activa con el mismo nombre
    c2 = crear_categoria(
        session_fixture,
        CategoriaCreate(nombre="Golosinas", descripcion="Nueva línea de golosinas"),
    )
    assert c2.id is not None
    assert c2.id != cat_id1
    assert c2.nombre == "Golosinas"
    assert c2.activo is True
    assert c2.anulado_at is None


# Consigna: docs/consignas_examen_2.md, 3.4/RN-03 y RN-13 — Validación de ID inexistente con HTTP 404.
def test_obtener_actualizar_anular_id_inexistente_lanza_404_rn03(session_fixture: Session):
    """Verifica que consultar, actualizar o anular una categoría inexistente retorne 404."""
    id_inexistente = 99999

    with pytest.raises(HTTPException) as exc_get:
        obtener_categoria(session_fixture, id_inexistente)
    assert exc_get.value.status_code == 404
    assert f"Categoría con id {id_inexistente} no encontrada." in exc_get.value.detail

    with pytest.raises(HTTPException) as exc_put:
        actualizar_categoria(
            session_fixture,
            id_inexistente,
            CategoriaUpdate(nombre="Inexistente"),
        )
    assert exc_put.value.status_code == 404
    assert f"Categoría con id {id_inexistente} no encontrada." in exc_put.value.detail

    with pytest.raises(HTTPException) as exc_del:
        anular_categoria(session_fixture, id_inexistente)
    assert exc_del.value.status_code == 404
    assert f"Categoría con id {id_inexistente} no encontrada." in exc_del.value.detail


# Consigna: docs/consignas_examen_2.md, 3.4/RN-04 — Rechazo de doble anulación con HTTP 409.
def test_anular_categoria_ya_anulada_lanza_409_rn04(session_fixture: Session):
    """Verifica que intentar anular una categoría que ya está anulada sea rechazado con 409."""
    cat = crear_categoria(session_fixture, CategoriaCreate(nombre="Panadería"))
    assert cat.id is not None

    anular_categoria(session_fixture, cat.id)
    session_fixture.refresh(cat)
    primer_anulado_at = cat.anulado_at
    assert primer_anulado_at is not None

    with pytest.raises(HTTPException) as exc_info:
        anular_categoria(session_fixture, cat.id)

    assert exc_info.value.status_code == 409
    assert f"La categoría con id {cat.id} ya se encuentra anulada." in exc_info.value.detail

    session_fixture.refresh(cat)
    assert cat.activo is False
    assert cat.anulado_at == primer_anulado_at


# Consigna: docs/consignas_examen_2.md, 3.4/RN-05 — Inmutabilidad de categorías anuladas con HTTP 409.
def test_actualizar_categoria_anulada_lanza_409_rn05(session_fixture: Session):
    """Verifica que PUT sobre una categoría anulada sea rechazado con 409 y preserve sus datos."""
    cat = crear_categoria(
        session_fixture,
        CategoriaCreate(nombre="Limpieza", descripcion="Artículos de aseo"),
    )
    assert cat.id is not None

    anular_categoria(session_fixture, cat.id)

    with pytest.raises(HTTPException) as exc_info:
        actualizar_categoria(
            session_fixture,
            cat.id,
            CategoriaUpdate(nombre="Limpieza Hogar", descripcion="Nuevo texto"),
        )

    assert exc_info.value.status_code == 409
    assert f"No se puede modificar la categoría con id {cat.id} porque se encuentra anulada." in exc_info.value.detail

    session_fixture.refresh(cat)
    assert cat.nombre == "Limpieza"
    assert cat.descripcion == "Artículos de aseo"
    assert cat.activo is False


# Consigna: docs/consignas_examen_2.md, 3.4/RN-02 y 4/R3 — Actualización exitosa y validación de conflicto de nombres.
def test_actualizar_categoria_exitoso_y_conflicto_nombre_rn02(session_fixture: Session):
    """Verifica actualización de atributos, conservación del propio nombre y conflicto con otra activa."""
    c1 = crear_categoria(session_fixture, CategoriaCreate(nombre="Snacks", descripcion="Salados"))
    c2 = crear_categoria(session_fixture, CategoriaCreate(nombre="Bebidas", descripcion="Refrescos"))
    assert c1.id is not None
    assert c2.id is not None

    # Actualizar nombre y descripción exitosamente
    act = actualizar_categoria(
        session_fixture,
        c1.id,
        CategoriaUpdate(nombre="Aperitivos", descripcion="Snacks y frutos secos"),
    )
    assert act.nombre == "Aperitivos"
    assert act.descripcion == "Snacks y frutos secos"

    # Actualizar conservando el mismo nombre (no debe colisionar consigo misma)
    act_mismo = actualizar_categoria(
        session_fixture,
        c1.id,
        CategoriaUpdate(nombre="Aperitivos", descripcion="Actualización menor"),
    )
    assert act_mismo.nombre == "Aperitivos"
    assert act_mismo.descripcion == "Actualización menor"

    # Intentar actualizar usando el nombre de otra categoría activa -> 409
    with pytest.raises(HTTPException) as exc_colision:
        actualizar_categoria(
            session_fixture,
            c1.id,
            CategoriaUpdate(nombre="Bebidas"),
        )
    assert exc_colision.value.status_code == 409
    assert "Ya existe otra categoría activa con el nombre 'Bebidas'." in exc_colision.value.detail

    # Anular c2 ("Bebidas") y verificar que c1 ahora sí puede renombrarse a "Bebidas" (RN-02)
    anular_categoria(session_fixture, c2.id)
    act_liberado = actualizar_categoria(
        session_fixture,
        c1.id,
        CategoriaUpdate(nombre="Bebidas", descripcion="Tomó el nombre liberado"),
    )
    assert act_liberado.nombre == "Bebidas"


# Consigna: docs/consignas_examen_2.md, 3.4/RN-06 y 4/R3 — Baja lógica de categoría no afecta productos clasificados.
def test_anular_categoria_no_anula_productos_clasificados_rn06(session_fixture: Session):
    """Verifica que anular una categoría no altere el estado operativo ni de stock de los productos asociados."""
    # 1. Crear unidad de medida de apoyo
    unidad = UnidadMedida(nombre="Kilogramo", simbolo="kg", tipo=TipoUnidad.peso)
    session_fixture.add(unidad)
    session_fixture.commit()
    session_fixture.refresh(unidad)

    # 2. Crear categoría
    cat = crear_categoria(session_fixture, CategoriaCreate(nombre="Frutas", descripcion="Frutas frescas"))
    assert cat.id is not None

    # 3. Crear producto clasificado en la categoría
    producto = Producto(
        unidad_venta_id=unidad.id,
        nombre="Manzanas Rojas",
        descripcion="Manzana deliciosa",
        precio_base=Decimal("1500.00"),
        stock_cantidad=Decimal("50.000"),
        disponible=True,
        activo=True,
        anulado_at=None,
    )
    session_fixture.add(producto)
    session_fixture.commit()
    session_fixture.refresh(producto)

    # 4. Vincular mediante ProductoCategoria
    vinculo = ProductoCategoria(
        producto_id=producto.id,
        categoria_id=cat.id,
        es_principal=True,
    )
    session_fixture.add(vinculo)
    session_fixture.commit()

    # 5. Ejecutar la anulación de la categoría
    anular_categoria(session_fixture, cat.id)

    session_fixture.refresh(cat)
    assert cat.activo is False
    assert cat.anulado_at is not None

    # RN-06: El producto debe permanecer activo y conservar su disponibilidad y stock intactos
    session_fixture.refresh(producto)
    assert producto.activo is True
    assert producto.anulado_at is None
    assert producto.disponible is True
    assert producto.stock_cantidad == Decimal("50.000")

    # El vínculo en la tabla asociativa se mantiene sin borrado físico en cascada
    relacion = session_fixture.get(ProductoCategoria, (producto.id, cat.id))
    assert relacion is not None
    assert relacion.es_principal is True


# Consigna: docs/consignas_examen_2.md, 4/R3 — Listado de categorías con filtros activo y search.
def test_listar_categorias_filtros_activo_y_search(session_fixture: Session):
    """Verifica listado ordenado por ID con combinaciones de filtros activo y search."""
    c_frescos = crear_categoria(session_fixture, CategoriaCreate(nombre="Frescos"))
    c_congelados = crear_categoria(session_fixture, CategoriaCreate(nombre="Congelados"))
    c_almacen = crear_categoria(session_fixture, CategoriaCreate(nombre="Almacén"))
    assert c_almacen.id is not None

    anular_categoria(session_fixture, c_almacen.id)

    # 1. Filtro por defecto (activo=None): solo activas
    activas_default = listar_categorias(session_fixture)
    assert [c.nombre for c in activas_default] == ["Frescos", "Congelados"]

    # 2. Filtro explícito activo=True
    activas_true = listar_categorias(session_fixture, activo=True)
    assert [c.nombre for c in activas_true] == ["Frescos", "Congelados"]

    # 3. Filtro explícito activo=False: solo anuladas
    anuladas = listar_categorias(session_fixture, activo=False)
    assert [c.nombre for c in anuladas] == ["Almacén"]

    # 4. Filtro search sobre activas (insensible a mayúsculas/minúsculas)
    search_gel = listar_categorias(session_fixture, search="gel")
    assert [c.nombre for c in search_gel] == ["Congelados"]

    search_fres = listar_categorias(session_fixture, search="FRES")
    assert [c.nombre for c in search_fres] == ["Frescos"]

    search_vacio = listar_categorias(session_fixture, search="inexistente")
    assert search_vacio == []

    # 5. Filtro search sobre anuladas
    search_anulado = listar_categorias(session_fixture, activo=False, search="alma")
    assert [c.nombre for c in search_anulado] == ["Almacén"]
