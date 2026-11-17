"""Pruebas de integración para endpoints y servicio de la relación N:N ProductoCategoria.

Consigna: docs/consignas_examen_2.md, 3.1, 3.4/RN-03, RN-06 a RN-09, RN-13, 4/R1, 4/R2, 4/R3, 6.1 y HU-P2-02.
"""

from datetime import datetime, timezone
from decimal import Decimal
import os
from typing import Generator
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, col, create_engine, select, text

import app.modules.categorias.model
import app.modules.productos.model
import app.modules.unidades_medida.model
from app.core.database import get_session
from app.main import app
from app.modules.categorias.model import Categoria
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
    """Crea una sesión transaccional aislada para pruebas de ProductoCategoria."""
    url, is_pg = _resolve_test_engine()

    if is_pg:
        schema_name = f"e24_{uuid.uuid4().hex}"
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
def client(session_fixture: Session) -> Generator[TestClient, None, None]:
    """Provee un TestClient con dependency_overrides apuntando a la sesión aislada."""
    def override_get_session():
        yield session_fixture

    app.dependency_overrides[get_session] = override_get_session
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()


def _seed_base_data(session: Session) -> tuple[int, int, int, int]:
    """Crea una unidad de medida, un producto activo y dos categorías activas."""
    unidad = UnidadMedida(
        nombre="Unidad",
        simbolo="u",
        tipo=TipoUnidad.contable,
    )
    session.add(unidad)
    session.flush()

    producto = Producto(
        unidad_venta_id=unidad.id,
        nombre="Yogur Natural",
        descripcion="Yogur entero natural 200g",
        precio_base=Decimal("250.00"),
        stock_cantidad=Decimal("15.000"),
        disponible=True,
        activo=True,
    )
    session.add(producto)
    session.flush()

    cat1 = Categoria(
        nombre="Lácteos",
        descripcion="Derivados lácteos y quesos",
        activo=True,
    )
    cat2 = Categoria(
        nombre="Bebidas",
        descripcion="Bebidas y refrigerios",
        activo=True,
    )
    session.add_all([cat1, cat2])
    session.commit()
    session.refresh(producto)
    session.refresh(cat1)
    session.refresh(cat2)

    return producto.id, cat1.id, cat2.id, unidad.id


# Consigna: docs/consignas_examen_2.md, 3.1, 4/R1, 4/R3, 6.1 y HU-P2-02.
def test_post_y_get_clasificar_producto_en_categorias_201_200(
    client: TestClient,
    session_fixture: Session,
):
    """Verifica POST /api/v1/productos/{id}/categorias (201) y GET /api/v1/productos/{id}/categorias (200)."""
    prod_id, cat1_id, cat2_id, _ = _seed_base_data(session_fixture)

    # 1. Asociar a Categoria 1 como principal
    payload_1 = {
        "categoria_id": cat1_id,
        "es_principal": True,
    }
    resp_post_1 = client.post(f"/api/v1/productos/{prod_id}/categorias", json=payload_1)
    assert resp_post_1.status_code == 201
    data_1 = resp_post_1.json()
    assert data_1["producto_id"] == prod_id
    assert data_1["categoria_id"] == cat1_id
    assert data_1["es_principal"] is True
    assert data_1["nombre"] == "Lácteos"
    assert data_1["activo"] is True
    assert data_1["categoria"]["id"] == cat1_id
    assert data_1["categoria"]["nombre"] == "Lácteos"

    # 2. Asociar a Categoria 2 como secundaria
    payload_2 = {
        "categoria_id": cat2_id,
        "es_principal": False,
    }
    resp_post_2 = client.post(f"/api/v1/productos/{prod_id}/categorias", json=payload_2)
    assert resp_post_2.status_code == 201
    data_2 = resp_post_2.json()
    assert data_2["producto_id"] == prod_id
    assert data_2["categoria_id"] == cat2_id
    assert data_2["es_principal"] is False
    assert data_2["nombre"] == "Bebidas"
    assert data_2["categoria"]["id"] == cat2_id

    # 3. Listar categorías del producto
    resp_get = client.get(f"/api/v1/productos/{prod_id}/categorias")
    assert resp_get.status_code == 200
    lista = resp_get.json()
    assert len(lista) == 2
    categorias_ids = [item["categoria_id"] for item in lista]
    assert cat1_id in categorias_ids
    assert cat2_id in categorias_ids

    # Verificar estado de es_principal en la lista
    item_cat1 = next(item for item in lista if item["categoria_id"] == cat1_id)
    item_cat2 = next(item for item in lista if item["categoria_id"] == cat2_id)
    assert item_cat1["es_principal"] is True
    assert item_cat2["es_principal"] is False


# Consigna: docs/consignas_examen_2.md, 3.4/RN-09 y 4/R3 — Reemplazo atómico de categoría principal.
def test_cambio_atomico_categoria_principal_rn09(
    client: TestClient,
    session_fixture: Session,
):
    """Verifica que al clasificar con es_principal=True la principal anterior pasa atómicamente a False."""
    prod_id, cat1_id, cat2_id, _ = _seed_base_data(session_fixture)

    # 1. Asociar Categoria 1 como principal
    resp_1 = client.post(
        f"/api/v1/productos/{prod_id}/categorias",
        json={"categoria_id": cat1_id, "es_principal": True},
    )
    assert resp_1.status_code == 201
    assert resp_1.json()["es_principal"] is True

    # 2. Asociar Categoria 2 también con es_principal=True
    resp_2 = client.post(
        f"/api/v1/productos/{prod_id}/categorias",
        json={"categoria_id": cat2_id, "es_principal": True},
    )
    assert resp_2.status_code == 201
    assert resp_2.json()["es_principal"] is True

    # 3. Verificar que Categoria 1 fue desmarcada y ahora solo Categoria 2 es principal
    resp_get = client.get(f"/api/v1/productos/{prod_id}/categorias")
    assert resp_get.status_code == 200
    lista = resp_get.json()

    item_cat1 = next(item for item in lista if item["categoria_id"] == cat1_id)
    item_cat2 = next(item for item in lista if item["categoria_id"] == cat2_id)
    assert item_cat1["es_principal"] is False
    assert item_cat2["es_principal"] is True

    # Comprobar unicidad en base de datos: exactamente 1 vínculo con es_principal=True
    principales_db = session_fixture.exec(
        select(ProductoCategoria).where(
            ProductoCategoria.producto_id == prod_id,
            col(ProductoCategoria.es_principal).is_(True),
        )
    ).all()
    assert len(principales_db) == 1
    assert principales_db[0].categoria_id == cat2_id


# Consigna: docs/consignas_examen_2.md, 3.4/RN-07 y RN-13 — Prohibición de doble clasificación.
def test_clasificar_dos_veces_misma_categoria_retorna_409_rn07(
    client: TestClient,
    session_fixture: Session,
):
    """Verifica que intentar asociar dos veces la misma categoría retorna 409 y no altera la BD."""
    prod_id, cat1_id, _, _ = _seed_base_data(session_fixture)

    # Primera asociación exitosa
    resp_ok = client.post(
        f"/api/v1/productos/{prod_id}/categorias",
        json={"categoria_id": cat1_id, "es_principal": False},
    )
    assert resp_ok.status_code == 201

    # Segundo intento con la misma categoría (incluso con es_principal=True)
    resp_conflict = client.post(
        f"/api/v1/productos/{prod_id}/categorias",
        json={"categoria_id": cat1_id, "es_principal": True},
    )
    assert resp_conflict.status_code == 409
    data_error = resp_conflict.json()
    assert "ya se encuentra clasificado en la categoría" in data_error["detail"]

    # Verificar que el vínculo original se mantuvo intacto con es_principal=False
    vinculo = session_fixture.get(ProductoCategoria, (prod_id, cat1_id))
    assert vinculo is not None
    assert vinculo.es_principal is False


# Consigna: docs/consignas_examen_2.md, 3.4/RN-08 y RN-13 — Rechazo de clasificaciones sobre entidades anuladas.
def test_clasificar_producto_anulado_o_categoria_anulada_retorna_409_rn08(
    client: TestClient,
    session_fixture: Session,
):
    """Verifica que no se puede asociar si el producto o la categoría se encuentran anulados."""
    prod_id, cat1_id, cat2_id, _ = _seed_base_data(session_fixture)

    # 1. Anular el producto y verificar rechazo 409
    producto = session_fixture.get(Producto, prod_id)
    assert producto is not None
    producto.activo = False
    producto.anulado_at = datetime.now(timezone.utc)
    session_fixture.add(producto)
    session_fixture.commit()

    resp_prod_anulado = client.post(
        f"/api/v1/productos/{prod_id}/categorias",
        json={"categoria_id": cat1_id, "es_principal": False},
    )
    assert resp_prod_anulado.status_code == 409
    assert "porque se encuentra anulado" in resp_prod_anulado.json()["detail"]

    # Reactivar el producto para probar categoría anulada
    producto.activo = True
    producto.anulado_at = None
    session_fixture.add(producto)
    session_fixture.commit()

    # 2. Anular la categoría cat2 vía endpoint DELETE
    resp_del_cat = client.delete(f"/api/v1/categorias/{cat2_id}")
    assert resp_del_cat.status_code == 204

    resp_get_cat = client.get(f"/api/v1/categorias/{cat2_id}")
    assert resp_get_cat.status_code == 200
    assert resp_get_cat.json()["activo"] is False

    # Intentar asociar en la categoría anulada
    resp_cat_anulada = client.post(
        f"/api/v1/productos/{prod_id}/categorias",
        json={"categoria_id": cat2_id, "es_principal": False},
    )
    assert resp_cat_anulada.status_code == 409
    assert "porque se encuentra anulada" in resp_cat_anulada.json()["detail"]

    # Verificar que no se persistió ningún vínculo
    vinculos = session_fixture.exec(
        select(ProductoCategoria).where(ProductoCategoria.producto_id == prod_id)
    ).all()
    assert len(vinculos) == 0


# Consigna: docs/consignas_examen_2.md, 3.4/RN-03 — Identificadores inexistentes retornan 404.
def test_clasificar_o_listar_con_id_inexistente_retorna_404_rn03(
    client: TestClient,
    session_fixture: Session,
):
    """Verifica respuestas 404 ante producto inexistente o categoría inexistente."""
    prod_id, cat1_id, _, _ = _seed_base_data(session_fixture)

    # Producto inexistente en POST
    resp_post_prod_404 = client.post(
        "/api/v1/productos/99999/categorias",
        json={"categoria_id": cat1_id, "es_principal": False},
    )
    assert resp_post_prod_404.status_code == 404
    assert "producto con id 99999 no encontrado" in resp_post_prod_404.json()["detail"].lower()

    # Categoría inexistente en POST
    resp_post_cat_404 = client.post(
        f"/api/v1/productos/{prod_id}/categorias",
        json={"categoria_id": 99999, "es_principal": False},
    )
    assert resp_post_cat_404.status_code == 404
    assert "categoría con id 99999 no encontrada" in resp_post_cat_404.json()["detail"].lower()

    # Producto inexistente en GET
    resp_get_prod_404 = client.get("/api/v1/productos/99999/categorias")
    assert resp_get_prod_404.status_code == 404
    assert "producto con id 99999 no encontrado" in resp_get_prod_404.json()["detail"].lower()


# Consigna: docs/consignas_examen_2.md, 4/R1 y 4/R3 — Validación de tipos y restricciones en entrada.
def test_validacion_payload_invalido_retorna_422(
    client: TestClient,
    session_fixture: Session,
):
    """Verifica que payloads inválidos (categoria_id <= 0 o ausente) retornen 422 Unprocessable Entity."""
    prod_id, _, _, _ = _seed_base_data(session_fixture)

    # categoria_id menor que 1 (ge=1)
    resp_ge = client.post(
        f"/api/v1/productos/{prod_id}/categorias",
        json={"categoria_id": 0, "es_principal": True},
    )
    assert resp_ge.status_code == 422

    # Falta campo obligatorio categoria_id
    resp_empty = client.post(
        f"/api/v1/productos/{prod_id}/categorias",
        json={"es_principal": True},
    )
    assert resp_empty.status_code == 422

    # Path id menor a 1 (ge=1)
    resp_path_ge = client.post(
        "/api/v1/productos/0/categorias",
        json={"categoria_id": 1, "es_principal": False},
    )
    assert resp_path_ge.status_code == 422


# Consigna: docs/consignas_examen_2.md, 4/R1, 4/R2 y HU-P2-02 — OpenAPI autodocumentado.
def test_openapi_registra_endpoints_producto_categorias(client: TestClient):
    """Verifica que /openapi.json documente POST y GET /api/v1/productos/{id}/categorias bajo tag Productos."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()

    path_key = "/api/v1/productos/{id}/categorias"
    assert path_key in schema["paths"]
    endpoint_spec = schema["paths"][path_key]

    assert "post" in endpoint_spec
    assert "get" in endpoint_spec
    assert "Productos" in endpoint_spec["post"]["tags"]
    assert "Productos" in endpoint_spec["get"]["tags"]

    # Verificar que los schemas estén documentados en components
    schemas = schema["components"]["schemas"]
    assert "ProductoCategoriaCreate" in schemas
    assert "ProductoCategoriaPublic" in schemas
