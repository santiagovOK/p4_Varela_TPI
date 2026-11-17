"""Pruebas unitarias aisladas para el servicio de lógica de negocio y persistencia de Productos.

Consigna: docs/consignas_examen_2.md, 3.1, 3.4/RN-01 a RN-13, 4/R2, 4/R3 y HU-P2-02.
"""

from collections.abc import Generator
from datetime import datetime, timezone
from decimal import Decimal
import os
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, col, select

from app.modules.categorias.model import Categoria
from app.modules.categorias.schema import CategoriaCreate
from app.modules.categorias.service import crear_categoria
from app.modules.productos.model import Producto, ProductoCategoria
from app.modules.productos.schema import (
    ProductoCategoriaCreate,
    ProductoCreate,
    ProductoPublic,
    ProductoUpdate,
)
from app.modules.productos.service import (
    actualizar_producto,
    anular_producto,
    clasificar_producto,
    crear_producto,
    listar_categorias_producto,
    listar_productos,
    obtener_producto,
)
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
    """Crea una sesión transaccional aislada para pruebas del servicio de productos."""
    url, is_pg = _resolve_test_engine()

    if is_pg:
        schema_name = f"e32_{uuid.uuid4().hex}"
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


@pytest.fixture(scope="function")
def unidades_fixture(session_fixture: Session) -> dict[str, UnidadMedida]:
    """Crea un juego estándar de unidades de medida (contable, peso, volumen) para los tests."""
    u_contable = UnidadMedida(nombre="Unidad", simbolo="un", tipo=TipoUnidad.contable)
    u_peso = UnidadMedida(nombre="Kilogramo", simbolo="kg", tipo=TipoUnidad.peso)
    u_volumen = UnidadMedida(nombre="Litro", simbolo="l", tipo=TipoUnidad.volumen)
    session_fixture.add_all([u_contable, u_peso, u_volumen])
    session_fixture.commit()
    session_fixture.refresh(u_contable)
    session_fixture.refresh(u_peso)
    session_fixture.refresh(u_volumen)
    return {
        "contable": u_contable,
        "peso": u_peso,
        "volumen": u_volumen,
    }


# ==============================================================================
# 1. Regla RN-10: Validación de stock entero para unidades contables (Create y Update)
# ==============================================================================

def test_crear_producto_contable_con_stock_entero_exitoso_rn10(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """RN-10: Crear producto contable con stock entero (e.g. 2.000) debe persistir exitosamente."""
    u_contable = unidades_fixture["contable"]
    assert u_contable.id is not None

    dto = ProductoCreate(
        nombre="Alfajor de Chocolate",
        descripcion="Alfajor triple relleno de dulce de leche",
        precio_base=Decimal("1500.50"),
        unidad_venta_id=u_contable.id,
        stock_cantidad=Decimal("2.000"),
        disponible=True,
    )

    prod = crear_producto(session_fixture, dto)

    assert isinstance(prod, ProductoPublic)
    assert prod.id is not None
    assert prod.nombre == "Alfajor de Chocolate"
    assert prod.stock_cantidad == Decimal("2.000")
    assert prod.hay_stock is True
    assert prod.unidad_venta.id == u_contable.id
    assert prod.unidad_venta.tipo == TipoUnidad.contable
    assert prod.activo is True
    assert prod.anulado_at is None
    assert prod.categorias == []


def test_crear_producto_contable_con_stock_fraccionario_lanza_422_rn10(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """RN-10 y RN-13: Crear producto contable con stock fraccionario falla con 422 y no persiste basura."""
    u_contable = unidades_fixture["contable"]
    assert u_contable.id is not None

    dto = ProductoCreate(
        nombre="Manzana individual",
        precio_base=Decimal("300.00"),
        unidad_venta_id=u_contable.id,
        stock_cantidad=Decimal("1.500"),
        disponible=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        crear_producto(session_fixture, dto)

    assert exc_info.value.status_code == 422
    assert "El stock debe ser un número entero para unidades de venta contables." in exc_info.value.detail

    # Atomicidad: no debe haber registros insertados
    registros = session_fixture.exec(select(Producto)).all()
    assert len(registros) == 0


@pytest.mark.parametrize("tipo_clave", ["peso", "volumen"])
def test_crear_producto_peso_y_volumen_permite_stock_fraccionario_rn10(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
    tipo_clave: str,
):
    """RN-10: Las unidades de peso y volumen aceptan stock fraccionario sin restricción."""
    u = unidades_fixture[tipo_clave]
    assert u.id is not None

    dto = ProductoCreate(
        nombre=f"Producto Fraccionario {tipo_clave}",
        precio_base=Decimal("2500.00"),
        unidad_venta_id=u.id,
        stock_cantidad=Decimal("1.750"),
        disponible=True,
    )

    prod = crear_producto(session_fixture, dto)
    assert prod.stock_cantidad == Decimal("1.750")
    assert prod.hay_stock is True
    assert prod.unidad_venta.tipo == u.tipo


def test_actualizar_producto_cambio_a_unidad_contable_con_stock_fraccionario_lanza_422_rn10(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """RN-10: Si un producto de peso con stock 1.5 cambia su unidad a contable manteniendo 1.5, falla con 422."""
    u_peso = unidades_fixture["peso"]
    u_contable = unidades_fixture["contable"]
    assert u_peso.id is not None
    assert u_contable.id is not None

    prod = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Queso Cremoso",
            precio_base=Decimal("4500.00"),
            unidad_venta_id=u_peso.id,
            stock_cantidad=Decimal("1.500"),
            disponible=True,
        ),
    )

    # Intento de cambio de unidad a contable conservando stock fraccionario
    update_dto = ProductoUpdate(
        nombre="Queso Cremoso",
        descripcion="Modificado",
        precio_base=Decimal("4500.00"),
        unidad_venta_id=u_contable.id,
        stock_cantidad=Decimal("1.500"),
        disponible=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        actualizar_producto(session_fixture, prod.id, update_dto)

    assert exc_info.value.status_code == 422
    assert "El stock debe ser un número entero para unidades de venta contables." in exc_info.value.detail

    # Verificar que el producto original sigue intacto
    recargado = obtener_producto(session_fixture, prod.id)
    assert recargado.unidad_venta.id == u_peso.id
    assert recargado.stock_cantidad == Decimal("1.500")


def test_actualizar_producto_cambio_stock_fraccionario_en_unidad_contable_lanza_422_rn10(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """RN-10: Mantener unidad contable e intentar actualizar stock a fraccionario lanza 422."""
    u_contable = unidades_fixture["contable"]
    assert u_contable.id is not None

    prod = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Paquete de Galletitas",
            precio_base=Decimal("900.00"),
            unidad_venta_id=u_contable.id,
            stock_cantidad=Decimal("10.000"),
            disponible=True,
        ),
    )

    update_dto = ProductoUpdate(
        nombre="Paquete de Galletitas",
        precio_base=Decimal("950.00"),
        unidad_venta_id=u_contable.id,
        stock_cantidad=Decimal("10.500"),
        disponible=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        actualizar_producto(session_fixture, prod.id, update_dto)

    assert exc_info.value.status_code == 422
    assert "El stock debe ser un número entero para unidades de venta contables." in exc_info.value.detail


def test_actualizar_producto_a_contable_con_stock_entero_exitoso(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """Actualizar producto modificando unidad a contable y stock a entero funciona y retorna DTO actualizado."""
    u_peso = unidades_fixture["peso"]
    u_contable = unidades_fixture["contable"]
    assert u_peso.id is not None
    assert u_contable.id is not None

    prod = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Naranjas por Kilo",
            precio_base=Decimal("1200.00"),
            unidad_venta_id=u_peso.id,
            stock_cantidad=Decimal("5.500"),
            disponible=True,
        ),
    )

    update_dto = ProductoUpdate(
        nombre="Naranjas por Bolsa",
        descripcion="Bolsa sellada de 2 unidades",
        precio_base=Decimal("2000.00"),
        unidad_venta_id=u_contable.id,
        stock_cantidad=Decimal("2.000"),
        disponible=True,
    )

    actualizado = actualizar_producto(session_fixture, prod.id, update_dto)
    assert actualizado.nombre == "Naranjas por Bolsa"
    assert actualizado.unidad_venta.id == u_contable.id
    assert actualizado.stock_cantidad == Decimal("2.000")
    assert actualizado.hay_stock is True


# ==============================================================================
# 2. Regla RN-11 y RN-12: Cálculo de hay_stock e independencia de disponible
# ==============================================================================

def test_hay_stock_calculado_segun_cantidad_e_independiente_de_disponible_rn11_rn12(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """RN-11 y RN-12: hay_stock es stock > 0 y disponible es independiente de hay_stock."""
    u_contable = unidades_fixture["contable"]
    assert u_contable.id is not None

    # Caso 1: stock > 0, disponible False -> hay_stock debe ser True
    prod1 = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Yerba Mate Edición Especial",
            precio_base=Decimal("3500.00"),
            unidad_venta_id=u_contable.id,
            stock_cantidad=Decimal("15.000"),
            disponible=False,
        ),
    )
    assert prod1.stock_cantidad == Decimal("15.000")
    assert prod1.disponible is False
    assert prod1.hay_stock is True

    # Caso 2: stock 0, disponible True -> hay_stock debe ser False
    prod2 = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Café Colombiano en Granos",
            precio_base=Decimal("8000.00"),
            unidad_venta_id=u_contable.id,
            stock_cantidad=Decimal("0.000"),
            disponible=True,
        ),
    )
    assert prod2.stock_cantidad == Decimal("0.000")
    assert prod2.disponible is True
    assert prod2.hay_stock is False

    # Actualizar prod1 llevando stock a 0 conservando disponible False
    update1 = ProductoUpdate(
        nombre="Yerba Mate Edición Especial",
        precio_base=Decimal("3500.00"),
        unidad_venta_id=u_contable.id,
        stock_cantidad=Decimal("0.000"),
        disponible=False,
    )
    actualizado1 = actualizar_producto(session_fixture, prod1.id, update1)
    assert actualizado1.stock_cantidad == Decimal("0.000")
    assert actualizado1.disponible is False
    assert actualizado1.hay_stock is False


# ==============================================================================
# 3. Validación RN-02 y RN-13: Unicidad activa y liberación de nombre por anulación
# ==============================================================================

def test_crear_producto_nombre_duplicado_activo_lanza_409_rn02(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """RN-02: Intentar crear un producto activo con nombre idéntico a otro activo lanza 409."""
    u = unidades_fixture["contable"]
    assert u.id is not None

    crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Agua Mineral 500ml",
            precio_base=Decimal("500.00"),
            unidad_venta_id=u.id,
            stock_cantidad=Decimal("50.000"),
            disponible=True,
        ),
    )

    dto_duplicado = ProductoCreate(
        nombre="Agua Mineral 500ml",
        precio_base=Decimal("600.00"),
        unidad_venta_id=u.id,
        stock_cantidad=Decimal("10.000"),
        disponible=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        crear_producto(session_fixture, dto_duplicado)

    assert exc_info.value.status_code == 409
    assert "Ya existe un producto activo con el nombre 'Agua Mineral 500ml'." in exc_info.value.detail


def test_actualizar_producto_nombre_propio_no_genera_conflicto(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """Actualizar un producto manteniendo su propio nombre no debe lanzar 409."""
    u = unidades_fixture["contable"]
    assert u.id is not None

    prod = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Fideos Spaghetti",
            precio_base=Decimal("800.00"),
            unidad_venta_id=u.id,
            stock_cantidad=Decimal("20.000"),
            disponible=True,
        ),
    )

    update_dto = ProductoUpdate(
        nombre="Fideos Spaghetti",
        descripcion="Fideos secos de trigo candeal",
        precio_base=Decimal("850.00"),
        unidad_venta_id=u.id,
        stock_cantidad=Decimal("25.000"),
        disponible=True,
    )

    actualizado = actualizar_producto(session_fixture, prod.id, update_dto)
    assert actualizado.nombre == "Fideos Spaghetti"
    assert actualizado.descripcion == "Fideos secos de trigo candeal"
    assert actualizado.precio_base == Decimal("850.00")


def test_actualizar_producto_a_nombre_de_otro_activo_lanza_409(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """Actualizar un producto a un nombre perteneciente a otro producto activo lanza 409."""
    u = unidades_fixture["contable"]
    assert u.id is not None

    p1 = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Arroz Blanco 1kg",
            precio_base=Decimal("1200.00"),
            unidad_venta_id=u.id,
            stock_cantidad=Decimal("10.000"),
            disponible=True,
        ),
    )
    p2 = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Arroz Integral 1kg",
            precio_base=Decimal("1400.00"),
            unidad_venta_id=u.id,
            stock_cantidad=Decimal("10.000"),
            disponible=True,
        ),
    )

    update_dto = ProductoUpdate(
        nombre="Arroz Blanco 1kg",  # En conflicto con p1
        precio_base=Decimal("1400.00"),
        unidad_venta_id=u.id,
        stock_cantidad=Decimal("10.000"),
        disponible=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        actualizar_producto(session_fixture, p2.id, update_dto)

    assert exc_info.value.status_code == 409
    assert "Ya existe otro producto activo con el nombre 'Arroz Blanco 1kg'." in exc_info.value.detail


def test_anular_producto_libera_nombre_para_nueva_alta_rn02_rn04(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """RN-02 y RN-04: La baja lógica de un producto libera su nombre para que otro activo lo utilice."""
    u = unidades_fixture["contable"]
    assert u.id is not None

    p1 = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Edición Limitada Verano",
            precio_base=Decimal("2000.00"),
            unidad_venta_id=u.id,
            stock_cantidad=Decimal("5.000"),
            disponible=True,
        ),
    )

    anular_producto(session_fixture, p1.id)

    # Debe ser posible crear uno nuevo con el mismo nombre
    p2 = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Edición Limitada Verano",
            precio_base=Decimal("2200.00"),
            unidad_venta_id=u.id,
            stock_cantidad=Decimal("8.000"),
            disponible=True,
        ),
    )
    assert p2.id != p1.id
    assert p2.activo is True


# ==============================================================================
# 4. Reglas RN-04, RN-05, RN-06: Anulación, inmutabilidad y preservación de relaciones
# ==============================================================================

def test_anular_producto_exitoso_y_persiste_stock_y_disponible(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """RN-04 y RN-06: Anular establece activo=False, fecha utc y conserva stock_cantidad y disponible."""
    u = unidades_fixture["contable"]
    assert u.id is not None

    prod = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Aceite de Oliva Extra Virgen",
            precio_base=Decimal("9500.00"),
            unidad_venta_id=u.id,
            stock_cantidad=Decimal("12.000"),
            disponible=True,
        ),
    )

    anular_producto(session_fixture, prod.id)

    # Consulta permitida por ID para entidades anuladas
    anulado = obtener_producto(session_fixture, prod.id)
    assert anulado.activo is False
    assert anulado.anulado_at is not None
    assert anulado.stock_cantidad == Decimal("12.000")
    assert anulado.disponible is True
    assert anulado.hay_stock is True


def test_anular_producto_ya_anulado_lanza_409_rn04(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """RN-04: Intentar anular dos veces el mismo producto lanza 409."""
    u = unidades_fixture["contable"]
    assert u.id is not None

    prod = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Vinagre de Manzana",
            precio_base=Decimal("1500.00"),
            unidad_venta_id=u.id,
            stock_cantidad=Decimal("5.000"),
            disponible=True,
        ),
    )
    anular_producto(session_fixture, prod.id)

    with pytest.raises(HTTPException) as exc_info:
        anular_producto(session_fixture, prod.id)

    assert exc_info.value.status_code == 409
    assert f"El producto con id {prod.id} ya se encuentra anulado." in exc_info.value.detail


def test_actualizar_producto_anulado_lanza_409_rn05(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """RN-05: Entidades anuladas son inmutables; PUT sobre anulado lanza 409."""
    u = unidades_fixture["contable"]
    assert u.id is not None

    prod = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Sal Fina 500g",
            precio_base=Decimal("400.00"),
            unidad_venta_id=u.id,
            stock_cantidad=Decimal("30.000"),
            disponible=True,
        ),
    )
    anular_producto(session_fixture, prod.id)

    update_dto = ProductoUpdate(
        nombre="Sal Fina 500g Modificada",
        precio_base=Decimal("450.00"),
        unidad_venta_id=u.id,
        stock_cantidad=Decimal("20.000"),
        disponible=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        actualizar_producto(session_fixture, prod.id, update_dto)

    assert exc_info.value.status_code == 409
    assert f"No se puede modificar el producto con id {prod.id} porque se encuentra anulado." in exc_info.value.detail


def test_producto_con_categorias_preserva_vinculos_y_orden_rn06(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """RN-06 y HU-P2-02: Producto con categorías las mapea ordenadas por ID; anular conserva vínculos."""
    u = unidades_fixture["contable"]
    assert u.id is not None

    c1 = crear_categoria(session_fixture, CategoriaCreate(nombre="Almacén"))
    c2 = crear_categoria(session_fixture, CategoriaCreate(nombre="Ofertas"))
    assert c1.id is not None and c2.id is not None

    prod = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Atún al Natural",
            precio_base=Decimal("2200.00"),
            unidad_venta_id=u.id,
            stock_cantidad=Decimal("15.000"),
            disponible=True,
        ),
    )

    # Clasificar en c2 como principal y c1 como secundaria
    clasificar_producto(
        session_fixture,
        prod.id,
        ProductoCategoriaCreate(categoria_id=c2.id, es_principal=True),
    )
    clasificar_producto(
        session_fixture,
        prod.id,
        ProductoCategoriaCreate(categoria_id=c1.id, es_principal=False),
    )

    detalle = obtener_producto(session_fixture, prod.id)
    assert len(detalle.categorias) == 2
    # Deben estar ordenadas por ID ascendente
    assert detalle.categorias[0].id == min(c1.id, c2.id)
    assert detalle.categorias[1].id == max(c1.id, c2.id)

    # Anular producto y verificar que los vínculos y listar_categorias_producto siguen intactos
    anular_producto(session_fixture, prod.id)
    detalle_post = obtener_producto(session_fixture, prod.id)
    assert len(detalle_post.categorias) == 2

    cats_vinculadas = listar_categorias_producto(session_fixture, prod.id)
    assert len(cats_vinculadas) == 2
    principal = [c for c in cats_vinculadas if c.es_principal]
    assert len(principal) == 1
    assert principal[0].categoria_id == c2.id


# ==============================================================================
# 5. Validación RN-03: IDs inexistentes
# ==============================================================================

def test_crear_producto_unidad_inexistente_lanza_404_rn03(session_fixture: Session):
    """RN-03: Crear producto con unidad_venta_id inexistente lanza 404."""
    dto = ProductoCreate(
        nombre="Producto Sin Unidad",
        precio_base=Decimal("100.00"),
        unidad_venta_id=99999,
        stock_cantidad=Decimal("1.000"),
        disponible=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        crear_producto(session_fixture, dto)

    assert exc_info.value.status_code == 404
    assert "Unidad de medida con id 99999 no encontrada." in exc_info.value.detail


def test_obtener_actualizar_anular_producto_inexistente_lanza_404_rn03(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """RN-03: Operaciones sobre ID inexistente lanzan 404."""
    u = unidades_fixture["contable"]
    assert u.id is not None

    with pytest.raises(HTTPException) as exc_get:
        obtener_producto(session_fixture, 88888)
    assert exc_get.value.status_code == 404
    assert "Producto con id 88888 no encontrado." in exc_get.value.detail

    with pytest.raises(HTTPException) as exc_put:
        actualizar_producto(
            session_fixture,
            88888,
            ProductoUpdate(
                nombre="Fantasma",
                precio_base=Decimal("10.00"),
                unidad_venta_id=u.id,
                stock_cantidad=Decimal("1.000"),
                disponible=True,
            ),
        )
    assert exc_put.value.status_code == 404
    assert "Producto con id 88888 no encontrado." in exc_put.value.detail

    with pytest.raises(HTTPException) as exc_del:
        anular_producto(session_fixture, 88888)
    assert exc_del.value.status_code == 404
    assert "Producto con id 88888 no encontrado." in exc_del.value.detail


# ==============================================================================
# 6. Listar productos: filtros (activo, disponible, categoria_id, search) y paginación
# ==============================================================================

def test_listar_productos_filtros_y_paginacion(
    session_fixture: Session,
    unidades_fixture: dict[str, UnidadMedida],
):
    """Verifica filtros de activo, disponible, categoria_id, search y paginación determinista por id ASC."""
    u_c = unidades_fixture["contable"]
    u_p = unidades_fixture["peso"]
    assert u_c.id is not None and u_p.id is not None

    cat_lacteos = crear_categoria(session_fixture, CategoriaCreate(nombre="Lácteos Frescos"))
    cat_bebidas = crear_categoria(session_fixture, CategoriaCreate(nombre="Bebidas Sin Alcohol"))
    assert cat_lacteos.id is not None and cat_bebidas.id is not None

    # p1: Activo, disponible True, Lácteos, stock > 0
    p1 = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Leche Entera 1L",
            precio_base=Decimal("1100.00"),
            unidad_venta_id=u_c.id,
            stock_cantidad=Decimal("20.000"),
            disponible=True,
        ),
    )
    clasificar_producto(
        session_fixture,
        p1.id,
        ProductoCategoriaCreate(categoria_id=cat_lacteos.id, es_principal=True),
    )

    # p2: Activo, disponible False, Lácteos y Bebidas, stock 0
    p2 = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Yogur Bebible Frutilla",
            precio_base=Decimal("1500.00"),
            unidad_venta_id=u_c.id,
            stock_cantidad=Decimal("0.000"),
            disponible=False,
        ),
    )
    clasificar_producto(
        session_fixture,
        p2.id,
        ProductoCategoriaCreate(categoria_id=cat_lacteos.id, es_principal=True),
    )
    clasificar_producto(
        session_fixture,
        p2.id,
        ProductoCategoriaCreate(categoria_id=cat_bebidas.id, es_principal=False),
    )

    # p3: Activo, disponible True, Bebidas, stock > 0
    p3 = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Jugo de Naranja 1L",
            precio_base=Decimal("1800.00"),
            unidad_venta_id=u_c.id,
            stock_cantidad=Decimal("15.000"),
            disponible=True,
        ),
    )
    clasificar_producto(
        session_fixture,
        p3.id,
        ProductoCategoriaCreate(categoria_id=cat_bebidas.id, es_principal=True),
    )

    # p4: Anulado, disponible True, stock > 0
    p4 = crear_producto(
        session_fixture,
        ProductoCreate(
            nombre="Queso Parmesano Rallado",
            precio_base=Decimal("2500.00"),
            unidad_venta_id=u_p.id,
            stock_cantidad=Decimal("5.500"),
            disponible=True,
        ),
    )
    anular_producto(session_fixture, p4.id)

    # 1. Filtro por defecto (activo=None): debe listar solo activos (p1, p2, p3)
    defecto = listar_productos(session_fixture)
    assert [p.id for p in defecto] == [p1.id, p2.id, p3.id]

    # 2. Filtro activo=False: debe listar solo anulados (p4)
    anulados = listar_productos(session_fixture, activo=False)
    assert [p.id for p in anulados] == [p4.id]
    assert anulados[0].activo is False

    # 3. Filtro disponible=True sobre activos: p1 y p3
    disp_true = listar_productos(session_fixture, disponible=True)
    assert [p.id for p in disp_true] == [p1.id, p3.id]

    # 4. Filtro disponible=False sobre activos: p2
    disp_false = listar_productos(session_fixture, disponible=False)
    assert [p.id for p in disp_false] == [p2.id]

    # 5. Filtro categoria_id:
    # Cat Lácteos tiene p1 y p2 (ambos activos)
    en_lacteos = listar_productos(session_fixture, categoria_id=cat_lacteos.id)
    assert [p.id for p in en_lacteos] == [p1.id, p2.id]

    # Cat Bebidas tiene p2 y p3 (ambos activos)
    en_bebidas = listar_productos(session_fixture, categoria_id=cat_bebidas.id)
    assert [p.id for p in en_bebidas] == [p2.id, p3.id]

    # Categoría sin productos o inexistente debe devolver lista vacía sin error
    en_vacia = listar_productos(session_fixture, categoria_id=99999)
    assert en_vacia == []

    # 6. Filtro search: insensible a mayúsculas y espacios
    busqueda_yogur = listar_productos(session_fixture, search="  YOGUR  ")
    assert [p.id for p in busqueda_yogur] == [p2.id]

    busqueda_1l = listar_productos(session_fixture, search="1l")
    assert [p.id for p in busqueda_1l] == [p1.id, p3.id]

    # 7. Combinación de filtros: categoría Lácteos + disponible True -> p1
    combinado = listar_productos(
        session_fixture,
        categoria_id=cat_lacteos.id,
        disponible=True,
    )
    assert [p.id for p in combinado] == [p1.id]

    # 8. Paginación: skip y limit
    pag1 = listar_productos(session_fixture, skip=0, limit=2)
    assert [p.id for p in pag1] == [p1.id, p2.id]

    pag2 = listar_productos(session_fixture, skip=2, limit=2)
    assert [p.id for p in pag2] == [p3.id]

    pag3 = listar_productos(session_fixture, skip=10, limit=2)
    assert pag3 == []
