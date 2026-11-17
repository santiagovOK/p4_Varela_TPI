"""Pruebas de integración para el router de categorías: endpoints CRUD, filtros, respuestas HTTP y OpenAPI.

Consigna: docs/consignas_examen_2.md, 4/R1, 4/R2, 4/R3, 6.1 y HU-P2-02.
"""

import os
import uuid
from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, text

# Consigna: docs/consignas_examen_2.md, 3.1 y 4/R3 — Registrar modelos para creación de tablas en SQLite o PostgreSQL.
import app.modules.categorias.model
import app.modules.productos.model
import app.modules.unidades_medida.model
from app.core.database import get_session
from app.main import app
from app.modules.categorias.model import Categoria
from app.modules.categorias.schema import CategoriaPublic
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
    """Crea una sesión transaccional aislada para pruebas de integración del router de categorías."""
    url, is_pg = _resolve_test_engine()

    if is_pg:
        schema_name = f"e23_{uuid.uuid4().hex}"
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
    """Provee un TestClient con dependency_overrides apuntando a la sesión de prueba aislada."""
    def override_get_session():
        yield session_fixture

    app.dependency_overrides[get_session] = override_get_session
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()

# Consigna: docs/consignas_examen_2.md, 4/R1, 4/R2, 6.1 y HU-P2-02 — POST y GET detalle.
def test_post_y_get_detalle_categoria_201_200(client: TestClient):
    """Verifica POST /api/v1/categorias (201) y GET /api/v1/categorias/{id} (200) con contrato CategoriaPublic."""
    payload = {
        "nombre": "Bebidas",
        "descripcion": "Gaseosas, aguas y jugos naturales",
    }
    response_post = client.post("/api/v1/categorias", json=payload)
    assert response_post.status_code == 201
    data_post = response_post.json()

    assert data_post["id"] is not None
    assert data_post["id"] >= 1
    assert data_post["nombre"] == "Bebidas"
    assert data_post["descripcion"] == "Gaseosas, aguas y jugos naturales"
    assert data_post["activo"] is True
    assert data_post["anulado_at"] is None

    # Validar serialización exacta contra CategoriaPublic
    categoria_public = CategoriaPublic(**data_post)
    assert categoria_public.id == data_post["id"]

    # GET detalle por ID
    cat_id = data_post["id"]
    response_get = client.get(f"/api/v1/categorias/{cat_id}")
    assert response_get.status_code == 200
    data_get = response_get.json()
    assert data_get == data_post

    # GET con ID inexistente retorna 404
    response_404 = client.get("/api/v1/categorias/99999")
    assert response_404.status_code == 404
    assert "no encontrada" in response_404.json()["detail"].lower()


# Consigna: docs/consignas_examen_2.md, 3.4/RN-01 y HU-P2-02 — Nombre < 3 chars devuelve 422.
def test_post_y_put_categoria_nombre_invalido_retorna_422_rn01(client: TestClient):
    """Verifica que POST y PUT con nombre menor a 3 caracteres o vacío retornen 422 Unprocessable Entity."""
    # POST con nombre de 2 caracteres
    res_post_corta = client.post("/api/v1/categorias", json={"nombre": "ab"})
    assert res_post_corta.status_code == 422

    # POST con nombre vacío
    res_post_vacia = client.post("/api/v1/categorias", json={"nombre": ""})
    assert res_post_vacia.status_code == 422

    # POST sin campo nombre
    res_post_sin_nombre = client.post("/api/v1/categorias", json={"descripcion": "Sin nombre"})
    assert res_post_sin_nombre.status_code == 422

    # Crear categoría válida
    res_valida = client.post("/api/v1/categorias", json={"nombre": "Verduras"})
    assert res_valida.status_code == 201
    cat_id = res_valida.json()["id"]

    # PUT con nombre inválido
    res_put_corta = client.put(f"/api/v1/categorias/{cat_id}", json={"nombre": "ve"})
    assert res_put_corta.status_code == 422

    # Verificar que el registro original permanece inalterado
    res_verif = client.get(f"/api/v1/categorias/{cat_id}")
    assert res_verif.status_code == 200
    assert res_verif.json()["nombre"] == "Verduras"


# Consigna: docs/consignas_examen_2.md, 3.4/RN-02, RN-13 y HU-P2-02 — Unicidad de nombre entre activas retorna 409.
def test_post_categoria_nombre_duplicado_activo_retorna_409_rn02(client: TestClient):
    """Verifica que intentar crear una categoría con nombre idéntico a una activa retorne 409 Conflict."""
    payload = {"nombre": "Panadería", "descripcion": "Panificados y masas"}
    res1 = client.post("/api/v1/categorias", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/categorias", json=payload)
    assert res2.status_code == 409
    assert "Ya existe una categoría activa con el nombre 'Panadería'." in res2.json()["detail"]


# Consigna: docs/consignas_examen_2.md, 4/R2, 4/R3 y HU-P2-02 — Filtros activo y search en GET /api/v1/categorias.
def test_get_categorias_filtros_activo_y_search_200(client: TestClient):
    """Verifica el listado de categorías con filtros activo (por defecto true, explicito true/false) y search."""
    # Crear tres categorías
    c1 = client.post("/api/v1/categorias", json={"nombre": "Lácteos y Quesos"}).json()
    c2 = client.post("/api/v1/categorias", json={"nombre": "Carnes Rojas"}).json()
    c3 = client.post("/api/v1/categorias", json={"nombre": "Limpieza y Desinfección"}).json()

    # Anular Carnes Rojas
    res_del = client.delete(f"/api/v1/categorias/{c2['id']}")
    assert res_del.status_code == 204

    # 1. GET por defecto (activo omitido): devuelve solo activas
    res_default = client.get("/api/v1/categorias")
    assert res_default.status_code == 200
    nombres_default = [item["nombre"] for item in res_default.json()]
    assert "Lácteos y Quesos" in nombres_default
    assert "Limpieza y Desinfección" in nombres_default
    assert "Carnes Rojas" not in nombres_default

    # 2. GET con activo=true explícito
    res_activas = client.get("/api/v1/categorias?activo=true")
    assert res_activas.status_code == 200
    nombres_activas = [item["nombre"] for item in res_activas.json()]
    assert nombres_activas == nombres_default

    # 3. GET con activo=false: devuelve solo anuladas
    res_anuladas = client.get("/api/v1/categorias?activo=false")
    assert res_anuladas.status_code == 200
    data_anuladas = res_anuladas.json()
    assert len(data_anuladas) == 1
    assert data_anuladas[0]["id"] == c2["id"]
    assert data_anuladas[0]["nombre"] == "Carnes Rojas"
    assert data_anuladas[0]["activo"] is False
    assert data_anuladas[0]["anulado_at"] is not None

    # 4. Filtro search insensible a mayúsculas/minúsculas sobre activas
    res_search1 = client.get("/api/v1/categorias?search=lácteos")
    assert res_search1.status_code == 200
    assert len(res_search1.json()) == 1
    assert res_search1.json()[0]["nombre"] == "Lácteos y Quesos"

    res_search_upper = client.get("/api/v1/categorias?search=QUESOS")
    assert res_search_upper.status_code == 200
    assert len(res_search_upper.json()) == 1
    assert res_search_upper.json()[0]["nombre"] == "Lácteos y Quesos"

    # 5. Filtro combinado activo=false y search
    res_search_anuladas = client.get("/api/v1/categorias?activo=false&search=carnes")
    assert res_search_anuladas.status_code == 200
    assert len(res_search_anuladas.json()) == 1
    assert res_search_anuladas.json()[0]["nombre"] == "Carnes Rojas"

    # 6. Búsqueda sin coincidencias
    res_search_empty = client.get("/api/v1/categorias?search=inexistente_xyz")
    assert res_search_empty.status_code == 200
    assert res_search_empty.json() == []


# Consigna: docs/consignas_examen_2.md, 3.4/RN-02, RN-03, RN-05 y HU-P2-02 — Actualización y conflictos.
def test_put_categoria_exitoso_y_conflictos_404_409_rn02_rn03_rn05(client: TestClient):
    """Verifica PUT exitoso, rechazo por nombre duplicado (409), ID inexistente (404) y entidad anulada (409)."""
    c1 = client.post("/api/v1/categorias", json={"nombre": "Golosinas", "descripcion": "Caramelos"}).json()
    c2 = client.post("/api/v1/categorias", json={"nombre": "Snacks", "descripcion": "Papas fritas"}).json()

    # Actualización exitosa con nuevo nombre y descripción
    res_update = client.put(
        f"/api/v1/categorias/{c1['id']}",
        json={"nombre": "Golosinas y Chocolates", "descripcion": "Dulces y chocolates"},
    )
    assert res_update.status_code == 200
    data_up = res_update.json()
    assert data_up["nombre"] == "Golosinas y Chocolates"
    assert data_up["descripcion"] == "Dulces y chocolates"

    # Actualización conservando el mismo nombre sobre la misma categoría (permitido)
    res_same = client.put(
        f"/api/v1/categorias/{c1['id']}",
        json={"nombre": "Golosinas y Chocolates", "descripcion": "Descripción actualizada"},
    )
    assert res_same.status_code == 200
    assert res_same.json()["descripcion"] == "Descripción actualizada"

    # Conflicto RN-02: actualizar c2 con el nombre existente de c1
    res_conflict = client.put(
        f"/api/v1/categorias/{c2['id']}",
        json={"nombre": "Golosinas y Chocolates", "descripcion": "Conflicto"},
    )
    assert res_conflict.status_code == 409
    assert "Ya existe otra categoría activa con el nombre 'Golosinas y Chocolates'." in res_conflict.json()["detail"]

    # Error RN-03: actualizar ID inexistente
    res_404 = client.put(
        "/api/v1/categorias/99999",
        json={"nombre": "Fantasma", "descripcion": "No existe"},
    )
    assert res_404.status_code == 404

    # Conflicto RN-05: intentar actualizar categoría previamente anulada
    client.delete(f"/api/v1/categorias/{c2['id']}")
    res_anulada_mod = client.put(
        f"/api/v1/categorias/{c2['id']}",
        json={"nombre": "Snacks Saludables", "descripcion": "Frutos secos"},
    )
    assert res_anulada_mod.status_code == 409
    assert "porque se encuentra anulada" in res_anulada_mod.json()["detail"]


# Consigna: docs/consignas_examen_2.md, 3.4/RN-02, RN-04 y HU-P2-02 — Anulación 204, doble anulación 409 y reutilización.
def test_delete_categoria_204_doble_anulacion_409_y_reutilizacion_nombre_rn02_rn04(client: TestClient):
    """Verifica DELETE (204), rechazo de doble anulación (409) y posterior reutilización de nombre (RN-02)."""
    c = client.post("/api/v1/categorias", json={"nombre": "Congelados"}).json()
    cat_id = c["id"]

    # 1. DELETE retorna 204 No Content
    res_del = client.delete(f"/api/v1/categorias/{cat_id}")
    assert res_del.status_code == 204
    assert res_del.text == ""

    # Verificar que el registro quedó marcado como anulado
    res_get = client.get(f"/api/v1/categorias/{cat_id}")
    assert res_get.status_code == 200
    assert res_get.json()["activo"] is False
    assert res_get.json()["anulado_at"] is not None

    # 2. Doble anulación retorna 409 Conflict (RN-04)
    res_del_dup = client.delete(f"/api/v1/categorias/{cat_id}")
    assert res_del_dup.status_code == 409
    assert "ya se encuentra anulada" in res_del_dup.json()["detail"]

    # 3. Anulación de ID inexistente retorna 404 (RN-03)
    res_del_404 = client.delete("/api/v1/categorias/99999")
    assert res_del_404.status_code == 404

    # 4. Reutilización de nombre (RN-02): crear nueva categoría con el mismo nombre "Congelados"
    res_reutil = client.post("/api/v1/categorias", json={"nombre": "Congelados"})
    assert res_reutil.status_code == 201
    nuevo_id = res_reutil.json()["id"]
    assert nuevo_id != cat_id
    assert res_reutil.json()["activo"] is True

    # Comprobar que en activas aparece la nueva y en anuladas la anterior
    res_activas = client.get("/api/v1/categorias?activo=true")
    assert any(item["id"] == nuevo_id for item in res_activas.json())
    assert not any(item["id"] == cat_id for item in res_activas.json())

    res_anuladas = client.get("/api/v1/categorias?activo=false")
    assert any(item["id"] == cat_id for item in res_anuladas.json())


# Consigna: docs/consignas_examen_2.md, 3.4/RN-06 y HU-P2-02 — Anular categoría no anula productos clasificados.
def test_delete_categoria_no_anula_producto_clasificado_rn06(
    client: TestClient,
    session_fixture: Session,
):
    """Verifica que la baja lógica de una categoría no altera el estado de sus productos asociados (RN-06)."""
    # 1. Crear unidad de medida, categoría y producto clasificado en la base
    unidad = UnidadMedida(nombre="kilogramo", simbolo="kg", tipo=TipoUnidad.peso)
    session_fixture.add(unidad)
    session_fixture.commit()
    session_fixture.refresh(unidad)

    cat = Categoria(nombre="Frutas y Verduras", activo=True, anulado_at=None)
    session_fixture.add(cat)
    session_fixture.commit()
    session_fixture.refresh(cat)

    prod = Producto(
        unidad_venta_id=unidad.id,
        nombre="Manzana Fuji",
        descripcion="Manzana fresca",
        precio_base=Decimal("1500.00"),
        stock_cantidad=Decimal("45.000"),
        disponible=True,
        activo=True,
        anulado_at=None,
    )
    session_fixture.add(prod)
    session_fixture.commit()
    session_fixture.refresh(prod)

    asociacion = ProductoCategoria(
        producto_id=prod.id,
        categoria_id=cat.id,
        es_principal=True,
    )
    session_fixture.add(asociacion)
    session_fixture.commit()

    # 2. Anular la categoría vía DELETE HTTP
    res_del = client.delete(f"/api/v1/categorias/{cat.id}")
    assert res_del.status_code == 204

    # 3. Refrescar producto y verificar que conserva activo=True y anulado_at=None
    session_fixture.refresh(prod)
    assert prod.activo is True
    assert prod.anulado_at is None

    # Verificar que la categoría sí quedó anulada
    session_fixture.refresh(cat)
    assert cat.activo is False
    assert cat.anulado_at is not None

    # Verificar que el vínculo se preserva
    session_fixture.refresh(asociacion)
    assert asociacion.categoria_id == cat.id
    assert asociacion.producto_id == prod.id


# Consigna: docs/consignas_examen_2.md, 4/R1 y 4/R3 — Verificación de rutas en OpenAPI/Swagger.
def test_openapi_registra_endpoints_categorias(client: TestClient):
    """Verifica que /openapi.json documente los endpoints de categorías con sus métodos HTTP y esquemas."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi = response.json()

    paths = openapi.get("paths", {})
    assert "/api/v1/categorias" in paths
    assert "/api/v1/categorias/{id}" in paths

    # Métodos en /api/v1/categorias
    assert "get" in paths["/api/v1/categorias"]
    assert "post" in paths["/api/v1/categorias"]
    assert "Categorías" in paths["/api/v1/categorias"]["get"]["tags"]
    assert "Categorías" in paths["/api/v1/categorias"]["post"]["tags"]

    # Métodos en /api/v1/categorias/{id}
    assert "get" in paths["/api/v1/categorias/{id}"]
    assert "put" in paths["/api/v1/categorias/{id}"]
    assert "delete" in paths["/api/v1/categorias/{id}"]
    assert "Categorías" in paths["/api/v1/categorias/{id}"]["get"]["tags"]
    assert "Categorías" in paths["/api/v1/categorias/{id}"]["put"]["tags"]
    assert "Categorías" in paths["/api/v1/categorias/{id}"]["delete"]["tags"]

    # Esquemas registrados
    schemas = openapi.get("components", {}).get("schemas", {})
    assert "CategoriaCreate" in schemas
    assert "CategoriaUpdate" in schemas
    assert "CategoriaPublic" in schemas
