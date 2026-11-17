"""Pruebas de integración HTTP aisladas para el router de productos.

Consigna: docs/consignas_examen_2.md, 3.1, 3.4, 4/R1, 4/R2, 4/R3, 6.1 y HU-P2-02.
Endpoints CRUD: POST /api/v1/productos, GET /api/v1/productos, GET /api/v1/productos/{id},
PUT /api/v1/productos/{id}, DELETE /api/v1/productos/{id}, junto con clasificación N:N.
"""

import logging
import os
import uuid
from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, text

import app.modules.categorias.model
import app.modules.productos.model
import app.modules.unidades_medida.model
from app.core.database import get_session
from app.main import app
from app.modules.categorias.model import Categoria
from app.modules.productos.model import Producto, ProductoCategoria
from app.modules.unidades_medida.model import TipoUnidad, UnidadMedida

logger = logging.getLogger(__name__)


def _resolve_test_engine() -> tuple[str, bool]:
    """Retorna un motor PostgreSQL si está accesible o SQLite in-memory como fallback determinista."""
    test_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if test_url and ("postgres" in test_url):
        try:
            probe = create_engine(test_url, echo=False)
            with probe.connect() as conn:
                conn.execute(text("SELECT 1"))
            probe.dispose()
            return test_url, True
        except Exception as exc:
            logger.debug(
                "PostgreSQL probe no disponible (%s). Usando fallback SQLite in-memory.",
                exc,
            )
    return "sqlite:///:memory:", False


@pytest.fixture(scope="function")
def session_fixture() -> Generator[Session, None, None]:
    """Crea una sesión transaccional aislada con esquema temporal en PostgreSQL o SQLite in-memory."""
    url, is_pg = _resolve_test_engine()

    if is_pg:
        schema_name = f"e33_{uuid.uuid4().hex}"
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
            u_contable = UnidadMedida(
                nombre="Unidad",
                simbolo="UN",
                tipo=TipoUnidad.contable,
            )
            u_peso = UnidadMedida(
                nombre="Kilogramo",
                simbolo="KG",
                tipo=TipoUnidad.peso,
            )
            u_volumen = UnidadMedida(
                nombre="Litro",
                simbolo="LT",
                tipo=TipoUnidad.volumen,
            )
            session.add_all([u_contable, u_peso, u_volumen])
            session.commit()
            session.refresh(u_contable)
            session.refresh(u_peso)
            session.refresh(u_volumen)

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
            u_contable = UnidadMedida(
                nombre="Unidad",
                simbolo="UN",
                tipo=TipoUnidad.contable,
            )
            u_peso = UnidadMedida(
                nombre="Kilogramo",
                simbolo="KG",
                tipo=TipoUnidad.peso,
            )
            u_volumen = UnidadMedida(
                nombre="Litro",
                simbolo="LT",
                tipo=TipoUnidad.volumen,
            )
            session.add_all([u_contable, u_peso, u_volumen])
            session.commit()
            session.refresh(u_contable)
            session.refresh(u_peso)
            session.refresh(u_volumen)

            yield session

        engine.dispose()


@pytest.fixture(scope="function")
def client(session_fixture: Session) -> Generator[TestClient, None, None]:
    """TestClient con override de get_session sin invocar lifespan de FastAPI."""
    def override_get_session():
        yield session_fixture

    app.dependency_overrides[get_session] = override_get_session
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
        test_client.close()


# ---------------------------------------------------------------------------
# 1. Ciclo de vida completo
# ---------------------------------------------------------------------------


def test_ciclo_vida_completo_producto(client: TestClient, session_fixture: Session):
    """Verifica POST (201), N:N (201), GET detalle (200), PUT (200), DELETE (204) y restricciones post-baja (409)."""
    # 1. POST producto: Pan integral, precio 10.50, stock 2, contable, disponible false -> 201
    payload_creacion = {
        "nombre": "Pan Integral Artesanal",
        "descripcion": "Pan 100% integral con semillas",
        "precio_base": "10.50",
        "unidad_venta_id": 1,
        "stock_cantidad": "2",
        "disponible": False,
    }
    resp_post = client.post("/api/v1/productos", json=payload_creacion)
    assert resp_post.status_code == 201
    data_post = resp_post.json()

    prod_id = data_post["id"]
    assert prod_id >= 1
    assert data_post["nombre"] == "Pan Integral Artesanal"
    assert Decimal(str(data_post["precio_base"])) == Decimal("10.50")
    assert Decimal(str(data_post["stock_cantidad"])) == Decimal("2")
    assert data_post["disponible"] is False
    assert data_post["activo"] is True
    assert data_post["anulado_at"] is None
    assert data_post["hay_stock"] is True
    assert data_post["unidad_venta"]["id"] == 1
    assert data_post["unidad_venta"]["simbolo"] == "UN"
    assert data_post["categorias"] == []

    # 2. Crear dos categorías vía HTTP para clasificar
    cat1 = client.post(
        "/api/v1/categorias",
        json={"nombre": "Panadería", "descripcion": "Productos panificados"},
    ).json()
    cat2 = client.post(
        "/api/v1/categorias",
        json={"nombre": "Saludables", "descripcion": "Opciones nutritivas"},
    ).json()

    # Clasificar en cat1 (no principal) y cat2 (principal)
    resp_n_n_1 = client.post(
        f"/api/v1/productos/{prod_id}/categorias",
        json={"categoria_id": cat1["id"], "es_principal": False},
    )
    assert resp_n_n_1.status_code == 201

    resp_n_n_2 = client.post(
        f"/api/v1/productos/{prod_id}/categorias",
        json={"categoria_id": cat2["id"], "es_principal": True},
    )
    assert resp_n_n_2.status_code == 201
    assert resp_n_n_2.json()["es_principal"] is True

    # 3. GET detalle producto: 200 con categorias asociadas
    resp_get = client.get(f"/api/v1/productos/{prod_id}")
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert len(data_get["categorias"]) == 2
    cat_ids = {c["id"] for c in data_get["categorias"]}
    assert cat_ids == {cat1["id"], cat2["id"]}

    # GET /api/v1/productos/{id}/categorias verifica la categoría principal
    resp_cat_rel = client.get(f"/api/v1/productos/{prod_id}/categorias")
    assert resp_cat_rel.status_code == 200
    items_rel = resp_cat_rel.json()
    assert len(items_rel) == 2
    principal = next(item for item in items_rel if item["es_principal"] is True)
    assert principal["categoria_id"] == cat2["id"]

    # 4. PUT producto con stock en 0: 200 con hay_stock=False
    payload_update = {
        "nombre": "Pan Integral Artesanal Orgánico",
        "descripcion": "Pan 100% integral orgánico certificado",
        "precio_base": "12.00",
        "unidad_venta_id": 1,
        "stock_cantidad": "0",
        "disponible": True,
    }
    resp_put = client.put(f"/api/v1/productos/{prod_id}", json=payload_update)
    assert resp_put.status_code == 200
    data_put = resp_put.json()
    assert data_put["nombre"] == "Pan Integral Artesanal Orgánico"
    assert Decimal(str(data_put["precio_base"])) == Decimal("12.00")
    assert Decimal(str(data_put["stock_cantidad"])) == Decimal("0")
    assert data_put["disponible"] is True
    assert data_put["hay_stock"] is False
    assert len(data_put["categorias"]) == 2

    # 5. DELETE anular producto: 204 con body vacío
    resp_delete = client.delete(f"/api/v1/productos/{prod_id}")
    assert resp_delete.status_code == 204
    assert resp_delete.content == b""

    # 6. GET detalle post-baja: activo=False, fecha no nula, stock/vínculos conservados
    resp_post_baja = client.get(f"/api/v1/productos/{prod_id}")
    assert resp_post_baja.status_code == 200
    data_baja = resp_post_baja.json()
    assert data_baja["activo"] is False
    assert data_baja["anulado_at"] is not None
    assert Decimal(str(data_baja["stock_cantidad"])) == Decimal("0")
    assert len(data_baja["categorias"]) == 2

    # 7. Intento de doble anulación: 409
    resp_re_delete = client.delete(f"/api/v1/productos/{prod_id}")
    assert resp_re_delete.status_code == 409
    assert "ya se encuentra anulado" in resp_re_delete.json()["detail"].lower()

    # 8. Intento de PUT sobre producto anulado: 409 (RN-05)
    resp_put_anulado = client.put(f"/api/v1/productos/{prod_id}", json=payload_update)
    assert resp_put_anulado.status_code == 409
    assert "anulado" in resp_put_anulado.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 2. Reglas de negocio vía HTTP (RN-02, RN-03, RN-10)
# ---------------------------------------------------------------------------


def test_rn10_stock_decimal_unidad_contable_rechazado_422(client: TestClient):
    """RN-10: Stock fraccionario en unidad contable debe responder 422 en POST y PUT."""
    payload_post = {
        "nombre": "Huevos Docena",
        "descripcion": "Docena de huevos de campo",
        "precio_base": "5.00",
        "unidad_venta_id": 1,  # UN (contable)
        "stock_cantidad": "1.5",
        "disponible": True,
    }
    resp_post = client.post("/api/v1/productos", json=payload_post)
    assert resp_post.status_code == 422
    assert "entero" in resp_post.json()["detail"].lower()

    # Crear primero con stock entero y luego intentar PUT con fraccionario
    payload_valido = {**payload_post, "stock_cantidad": "3"}
    resp_creado = client.post("/api/v1/productos", json=payload_valido)
    assert resp_creado.status_code == 201
    prod_id = resp_creado.json()["id"]

    payload_put_frac = {**payload_valido, "stock_cantidad": "4.25"}
    resp_put = client.put(f"/api/v1/productos/{prod_id}", json=payload_put_frac)
    assert resp_put.status_code == 422
    assert "entero" in resp_put.json()["detail"].lower()

    # Confirmar que el stock persistido no cambió
    resp_get = client.get(f"/api/v1/productos/{prod_id}")
    assert Decimal(str(resp_get.json()["stock_cantidad"])) == Decimal("3")


def test_stock_fraccionario_permitido_en_peso_y_volumen(client: TestClient):
    """Unidades de tipo peso (KG) y volumen (LT) admiten stock con decimales en POST y PUT."""
    # 1. Unidad peso (id=2, KG)
    payload_peso = {
        "nombre": "Queso Parmesano",
        "precio_base": "25.00",
        "unidad_venta_id": 2,
        "stock_cantidad": "12.75",
        "disponible": True,
    }
    resp_peso = client.post("/api/v1/productos", json=payload_peso)
    assert resp_peso.status_code == 201
    assert Decimal(str(resp_peso.json()["stock_cantidad"])) == Decimal("12.75")
    peso_id = resp_peso.json()["id"]

    # PUT con otra fracción
    payload_peso["stock_cantidad"] = "8.125"
    resp_put_peso = client.put(f"/api/v1/productos/{peso_id}", json=payload_peso)
    assert resp_put_peso.status_code == 200
    assert Decimal(str(resp_put_peso.json()["stock_cantidad"])) == Decimal("8.125")

    # 2. Unidad volumen (id=3, LT)
    payload_vol = {
        "nombre": "Aceite de Oliva Extra Virgen",
        "precio_base": "18.50",
        "unidad_venta_id": 3,
        "stock_cantidad": "5.5",
        "disponible": True,
    }
    resp_vol = client.post("/api/v1/productos", json=payload_vol)
    assert resp_vol.status_code == 201
    assert Decimal(str(resp_vol.json()["stock_cantidad"])) == Decimal("5.5")


def test_unidad_venta_inexistente_retorna_404(client: TestClient):
    """RN-03: Crear producto con unidad de venta inexistente retorna 404."""
    payload = {
        "nombre": "Producto Sin Unidad",
        "precio_base": "10.00",
        "unidad_venta_id": 999,
        "stock_cantidad": "5",
        "disponible": True,
    }
    resp = client.post("/api/v1/productos", json=payload)
    assert resp.status_code == 404
    assert "unidad de medida" in resp.json()["detail"].lower()


def test_unicidad_nombre_producto_activo_retorna_409(client: TestClient):
    """RN-02: Nombre duplicado entre productos activos retorna 409 en POST y PUT."""
    payload1 = {
        "nombre": "Leche Entera",
        "precio_base": "1.20",
        "unidad_venta_id": 3,
        "stock_cantidad": "20",
        "disponible": True,
    }
    resp1 = client.post("/api/v1/productos", json=payload1)
    assert resp1.status_code == 201

    # POST con el mismo nombre -> 409
    resp_duplicado = client.post("/api/v1/productos", json=payload1)
    assert resp_duplicado.status_code == 409
    assert "ya existe un producto activo" in resp_duplicado.json()["detail"].lower()

    # Crear un segundo producto con otro nombre
    payload2 = {
        "nombre": "Leche Descremada",
        "precio_base": "1.30",
        "unidad_venta_id": 3,
        "stock_cantidad": "15",
        "disponible": True,
    }
    resp2 = client.post("/api/v1/productos", json=payload2)
    assert resp2.status_code == 201
    id2 = resp2.json()["id"]

    # PUT en producto 2 intentando renombrar al nombre del producto 1 -> 409
    payload_conflicto = {**payload2, "nombre": "Leche Entera"}
    resp_put_conflict = client.put(f"/api/v1/productos/{id2}", json=payload_conflicto)
    assert resp_put_conflict.status_code == 409
    assert "ya existe otro producto activo" in resp_put_conflict.json()["detail"].lower()


def test_producto_inexistente_retorna_404_en_rutas_con_id(client: TestClient):
    """GET, PUT y DELETE sobre producto inexistente retornan 404."""
    inexistente_id = 99999

    assert client.get(f"/api/v1/productos/{inexistente_id}").status_code == 404

    payload = {
        "nombre": "Inexistente",
        "precio_base": "1.00",
        "unidad_venta_id": 1,
        "stock_cantidad": "1",
        "disponible": True,
    }
    assert client.put(f"/api/v1/productos/{inexistente_id}", json=payload).status_code == 404
    assert client.delete(f"/api/v1/productos/{inexistente_id}").status_code == 404


# ---------------------------------------------------------------------------
# 3. Validaciones de esquema HTTP Query y Path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("params", "descripcion"),
    [
        ({"skip": -1}, "skip negativo"),
        ({"limit": 0}, "limit cero menor al mínimo"),
        ({"limit": 51}, "limit 51 mayor al máximo 50"),
        ({"categoria_id": 0}, "categoria_id 0 menor a 1"),
        ({"categoria_id": -5}, "categoria_id negativo"),
        ({"activo": "invalido"}, "activo no booleano"),
        ({"disponible": "no_es_bool"}, "disponible no booleano"),
    ],
)
def test_validaciones_query_params_invalidos_retornan_422(
    client: TestClient,
    params: dict,
    descripcion: str,
):
    """Verifica que parámetros Query fuera de rango o mal tipados respondan 422."""
    resp = client.get("/api/v1/productos", params=params)
    assert resp.status_code == 422, f"Fallo en: {descripcion}"


@pytest.mark.parametrize(
    "path_id",
    [0, -1, "abc", "null"],
)
def test_validaciones_path_id_invalido_retorna_422(client: TestClient, path_id):
    """Verifica que id en Path menor a 1 o no entero retorne 422 en GET, PUT y DELETE."""
    assert client.get(f"/api/v1/productos/{path_id}").status_code == 422
    assert (
        client.put(
            f"/api/v1/productos/{path_id}",
            json={
                "nombre": "Test",
                "precio_base": "1.00",
                "unidad_venta_id": 1,
                "disponible": True,
            },
        ).status_code
        == 422
    )
    assert client.delete(f"/api/v1/productos/{path_id}").status_code == 422


def test_limites_validos_query_params_aceptados(client: TestClient):
    """Valida los límites permitidos: skip=0, limit=1 y limit=50."""
    for params in [{"skip": 0, "limit": 1}, {"skip": 0, "limit": 50}]:
        resp = client.get("/api/v1/productos", params=params)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.parametrize(
    ("body_invalido", "descripcion"),
    [
        (
            {
                "nombre": "AB",  # < 3 caracteres
                "precio_base": "10.00",
                "unidad_venta_id": 1,
                "disponible": True,
            },
            "nombre menor a 3 caracteres",
        ),
        (
            {
                "nombre": "Válido",
                "precio_base": "-5.00",  # negativo
                "unidad_venta_id": 1,
                "disponible": True,
            },
            "precio negativo",
        ),
        (
            {
                "nombre": "Válido",
                "precio_base": "10.00",
                "unidad_venta_id": 0,  # ge=1
                "disponible": True,
            },
            "unidad_venta_id menor a 1",
        ),
        (
            {
                "nombre": "Válido",
                "precio_base": "10.00",
                "unidad_venta_id": 1,
                "stock_cantidad": "-1",  # negativo
                "disponible": True,
            },
            "stock negativo",
        ),
        (
            {
                # Falta disponible
                "nombre": "Válido",
                "precio_base": "10.00",
                "unidad_venta_id": 1,
            },
            "campo requerido faltante",
        ),
    ],
)
def test_validaciones_body_producto_invalido_retorna_422(
    client: TestClient,
    body_invalido: dict,
    descripcion: str,
):
    """POST y PUT con campos inválidos o ausentes deben retornar 422."""
    resp_post = client.post("/api/v1/productos", json=body_invalido)
    assert resp_post.status_code == 422, f"POST fallo en: {descripcion}"

    resp_put = client.put("/api/v1/productos/1", json=body_invalido)
    assert resp_put.status_code == 422, f"PUT fallo en: {descripcion}"


# ---------------------------------------------------------------------------
# 4. Dataset determinista de 12 productos: paginación y filtros
# ---------------------------------------------------------------------------


def test_dataset_12_productos_paginacion_y_filtros(client: TestClient):
    """Paginación y filtros con dataset determinista de 12 productos creados vía HTTP."""
    # Crear dos categorías
    cat_pan = client.post(
        "/api/v1/categorias",
        json={"nombre": "Panaderia Fresca", "descripcion": "Horneados del día"},
    ).json()
    cat_lacteos = client.post(
        "/api/v1/categorias",
        json={"nombre": "Lácteos y Derivados", "descripcion": "Frescos refrigerados"},
    ).json()

    # Creación de 12 productos deterministas
    # Índices 0 a 11:
    # - 10 activos (0 a 9) y 2 anulados (10 y 11)
    # - disponible alternado (par -> True, impar -> False)
    # - nombres con variación de mayúsculas/palabras clave
    dataset = [
        {"nombre": "Alfajor de Chocolate", "precio": "2.50", "u": 1, "disp": True},
        {"nombre": "Alfajor de Maicena", "precio": "2.20", "u": 1, "disp": False},
        {"nombre": "Baguette Tradicional", "precio": "1.80", "u": 1, "disp": True},
        {"nombre": "Bizcocho de Grasa", "precio": "3.00", "u": 2, "disp": False},
        {"nombre": "Croissant Francés", "precio": "2.80", "u": 1, "disp": True},
        {"nombre": "Dulce de Leche Repostero", "precio": "5.50", "u": 2, "disp": False},
        {"nombre": "Empanada de Carne", "precio": "1.50", "u": 1, "disp": True},
        {"nombre": "Flan Casero", "precio": "3.50", "u": 1, "disp": False},
        {"nombre": "Galletitas Dulces", "precio": "2.00", "u": 1, "disp": True},
        {"nombre": "Helado Artesanal", "precio": "9.00", "u": 2, "disp": False},
        {"nombre": "Infusión de Té Verde", "precio": "1.10", "u": 1, "disp": True},
        {"nombre": "Jugo de Naranja Natural", "precio": "2.90", "u": 3, "disp": False},
    ]

    creados = []
    for item in dataset:
        resp = client.post(
            "/api/v1/productos",
            json={
                "nombre": item["nombre"],
                "precio_base": item["precio"],
                "unidad_venta_id": item["u"],
                "stock_cantidad": "10",
                "disponible": item["disp"],
            },
        )
        assert resp.status_code == 201
        creados.append(resp.json())

    # Anular los últimos 2 productos (índices 10 y 11)
    resp_del1 = client.delete(f"/api/v1/productos/{creados[10]['id']}")
    assert resp_del1.status_code == 204
    resp_del2 = client.delete(f"/api/v1/productos/{creados[11]['id']}")
    assert resp_del2.status_code == 204

    # Clasificar productos 0, 1, 2 en cat_pan
    for idx in (0, 1, 2):
        client.post(
            f"/api/v1/productos/{creados[idx]['id']}/categorias",
            json={"categoria_id": cat_pan["id"], "es_principal": (idx == 0)},
        )

    # Clasificar productos 2, 5 en cat_lacteos (producto 2 tiene 2 categorías)
    for idx in (2, 5):
        client.post(
            f"/api/v1/productos/{creados[idx]['id']}/categorias",
            json={"categoria_id": cat_lacteos["id"], "es_principal": False},
        )

    # --- Paginación default (limit=10, skip=0) ---
    # Activos son 10 (índices 0..9). Página 1 debe traer exactamente los 10
    resp_p1 = client.get("/api/v1/productos")
    assert resp_p1.status_code == 200
    p1_items = resp_p1.json()
    assert len(p1_items) == 10
    p1_ids = [p["id"] for p in p1_items]
    assert p1_ids == [creados[i]["id"] for i in range(10)]

    # Página 2 (skip=10, limit=10): vacía porque solo hay 10 activos
    resp_p2 = client.get("/api/v1/productos", params={"skip": 10, "limit": 10})
    assert resp_p2.status_code == 200
    assert resp_p2.json() == []

    # Paginación en bloques de 4
    resp_b1 = client.get("/api/v1/productos", params={"skip": 0, "limit": 4})
    resp_b2 = client.get("/api/v1/productos", params={"skip": 4, "limit": 4})
    resp_b3 = client.get("/api/v1/productos", params={"skip": 8, "limit": 4})
    ids_b1 = [p["id"] for p in resp_b1.json()]
    ids_b2 = [p["id"] for p in resp_b2.json()]
    ids_b3 = [p["id"] for p in resp_b3.json()]
    assert len(ids_b1) == 4
    assert len(ids_b2) == 4
    assert len(ids_b3) == 2
    # Sin solapamientos ni omisiones
    assert ids_b1 + ids_b2 + ids_b3 == [creados[i]["id"] for i in range(10)]

    # --- Filtro activo ---
    # activo=true explícito
    resp_activos = client.get("/api/v1/productos", params={"activo": "true", "limit": 50})
    assert len(resp_activos.json()) == 10

    # activo=false (anulados)
    resp_anulados = client.get("/api/v1/productos", params={"activo": "false", "limit": 50})
    assert resp_anulados.status_code == 200
    items_anulados = resp_anulados.json()
    assert len(items_anulados) == 2
    anulados_ids = {p["id"] for p in items_anulados}
    assert anulados_ids == {creados[10]["id"], creados[11]["id"]}
    assert all(p["activo"] is False for p in items_anulados)

    # --- Filtro disponible ---
    # Entre los 10 activos: pares son disp=True (0, 2, 4, 6, 8 -> 5 items)
    resp_disp_true = client.get(
        "/api/v1/productos",
        params={"disponible": "true", "limit": 50},
    )
    assert resp_disp_true.status_code == 200
    ids_disp_true = [p["id"] for p in resp_disp_true.json()]
    assert ids_disp_true == [creados[i]["id"] for i in (0, 2, 4, 6, 8)]

    # Impares son disp=False (1, 3, 5, 7, 9 -> 5 items)
    resp_disp_false = client.get(
        "/api/v1/productos",
        params={"disponible": "false", "limit": 50},
    )
    assert resp_disp_false.status_code == 200
    ids_disp_false = [p["id"] for p in resp_disp_false.json()]
    assert ids_disp_false == [creados[i]["id"] for i in (1, 3, 5, 7, 9)]

    # --- Filtro search (case-insensitive y whitespace) ---
    # Buscar "ALFAJOR" con espacios debe traer los 2 alfajores
    resp_search_upper = client.get(
        "/api/v1/productos",
        params={"search": "  ALFAJOR  "},
    )
    assert resp_search_upper.status_code == 200
    search_ids = [p["id"] for p in resp_search_upper.json()]
    assert search_ids == [creados[0]["id"], creados[1]["id"]]

    # Buscar "fLaN" -> 1 flan
    resp_flan = client.get("/api/v1/productos", params={"search": "fLaN"})
    assert resp_flan.status_code == 200
    assert len(resp_flan.json()) == 1
    assert resp_flan.json()[0]["id"] == creados[7]["id"]

    # Search sin coincidencias -> lista vacía
    resp_no_match = client.get("/api/v1/productos", params={"search": "inexistente_xyz"})
    assert resp_no_match.status_code == 200
    assert resp_no_match.json() == []

    # --- Filtro categoria_id ---
    # cat_pan vinculada a 0, 1, 2
    resp_cat_pan = client.get(
        "/api/v1/productos",
        params={"categoria_id": cat_pan["id"]},
    )
    assert resp_cat_pan.status_code == 200
    ids_cat_pan = [p["id"] for p in resp_cat_pan.json()]
    assert ids_cat_pan == [creados[0]["id"], creados[1]["id"], creados[2]["id"]]

    # cat_lacteos vinculada a 2, 5
    resp_cat_lact = client.get(
        "/api/v1/productos",
        params={"categoria_id": cat_lacteos["id"]},
    )
    assert resp_cat_lact.status_code == 200
    ids_cat_lact = [p["id"] for p in resp_cat_lact.json()]
    assert ids_cat_lact == [creados[2]["id"], creados[5]["id"]]

    # Categoría existente sin productos clasificados -> lista vacía 200 []
    cat_vacia = client.post(
        "/api/v1/categorias",
        json={"nombre": "Bebidas Alcohólicas", "descripcion": "Vinos y licores"},
    ).json()
    resp_cat_vacia = client.get(
        "/api/v1/productos",
        params={"categoria_id": cat_vacia["id"]},
    )
    assert resp_cat_vacia.status_code == 200
    assert resp_cat_vacia.json() == []

    # --- Filtros combinados con AND ---
    # categoria_id=cat_pan (0, 1, 2) AND disponible=true (0, 2)
    resp_comb = client.get(
        "/api/v1/productos",
        params={"categoria_id": cat_pan["id"], "disponible": "true"},
    )
    assert resp_comb.status_code == 200
    assert [p["id"] for p in resp_comb.json()] == [creados[0]["id"], creados[2]["id"]]

    # categoria_id=cat_pan (0, 1, 2) AND search="maicena" -> solo producto 1
    resp_comb_search = client.get(
        "/api/v1/productos",
        params={"categoria_id": cat_pan["id"], "search": "maicena"},
    )
    assert resp_comb_search.status_code == 200
    assert len(resp_comb_search.json()) == 1
    assert resp_comb_search.json()[0]["id"] == creados[1]["id"]

    # Paginación sobre resultado filtrado (disponible=true son 5: 0, 2, 4, 6, 8)
    # limit=2, skip=2 -> productos 4 y 6
    resp_pag_filtrada = client.get(
        "/api/v1/productos",
        params={"disponible": "true", "skip": 2, "limit": 2},
    )
    assert resp_pag_filtrada.status_code == 200
    assert [p["id"] for p in resp_pag_filtrada.json()] == [creados[4]["id"], creados[6]["id"]]


def test_put_unidad_venta_inexistente_y_aislamiento_baja_categoria_rn03_rn06(client: TestClient):
    """RN-03 y RN-06: PUT con unidad inexistente retorna 404 y baja lógica de categoría no altera producto."""
    # 1. Crear producto activo
    payload_creacion = {
        "nombre": "Queso Artesanal",
        "descripcion": "Queso semiduro estacionado",
        "precio_base": "850.00",
        "unidad_venta_id": 2,  # Kilogramo
        "stock_cantidad": "4.50",
        "disponible": True,
    }
    resp_create = client.post("/api/v1/productos", json=payload_creacion)
    assert resp_create.status_code == 201
    prod = resp_create.json()
    prod_id = prod["id"]
    assert prod["unidad_venta"]["id"] == 2

    # 2. PUT con unidad_venta_id inexistente (99999) -> 404 Not Found con mensaje sobre unidad de medida (RN-03)
    resp_put_invalida = client.put(
        f"/api/v1/productos/{prod_id}",
        json={**payload_creacion, "unidad_venta_id": 99999},
    )
    assert resp_put_invalida.status_code == 404
    assert "unidad de medida" in resp_put_invalida.json()["detail"].lower()

    # Verificar que el producto conserva intacta su unidad_venta_id == 2
    resp_get_check = client.get(f"/api/v1/productos/{prod_id}")
    assert resp_get_check.status_code == 200
    assert resp_get_check.json()["unidad_venta"]["id"] == 2

    # 3. Crear categoría, clasificar producto, dar de baja lógica y verificar aislamiento (RN-06)
    resp_cat = client.post(
        "/api/v1/categorias",
        json={"nombre": "Fiambrería", "descripcion": "Fiambres y embutidos"},
    )
    assert resp_cat.status_code == 201
    cat_id = resp_cat.json()["id"]

    resp_clasif = client.post(
        f"/api/v1/productos/{prod_id}/categorias",
        json={"categoria_id": cat_id, "es_principal": True},
    )
    assert resp_clasif.status_code == 201

    # Baja lógica de la categoría (204 No Content)
    resp_del_cat = client.delete(f"/api/v1/categorias/{cat_id}")
    assert resp_del_cat.status_code == 204

    # RN-06: El producto conserva activo=True, disponible=True, hay_stock=True y su vínculo histórico
    resp_get_prod = client.get(f"/api/v1/productos/{prod_id}")
    assert resp_get_prod.status_code == 200
    data_prod = resp_get_prod.json()
    assert data_prod["activo"] is True
    assert data_prod["disponible"] is True
    assert data_prod["hay_stock"] is True
    assert any(c["id"] == cat_id for c in data_prod["categorias"])

    # Y al listar por categoria_id, el producto aún figura asociado históricamente
    resp_list_cat = client.get("/api/v1/productos", params={"categoria_id": cat_id})
    assert resp_list_cat.status_code == 200
    ids_en_cat = [p["id"] for p in resp_list_cat.json()]
    assert prod_id in ids_en_cat


def test_openapi_registra_cinco_endpoints_y_schemas_productos(client: TestClient):
    """Verifica que /openapi.json documenta los cinco endpoints CRUD de productos y sus schemas."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()

    paths = schema.get("paths", {})
    assert "/api/v1/productos" in paths
    assert "get" in paths["/api/v1/productos"]
    assert "post" in paths["/api/v1/productos"]

    assert "/api/v1/productos/{id}" in paths
    assert "get" in paths["/api/v1/productos/{id}"]
    assert "put" in paths["/api/v1/productos/{id}"]
    assert "delete" in paths["/api/v1/productos/{id}"]

    components = schema.get("components", {}).get("schemas", {})
    for expected_schema in [
        "ProductoCreate",
        "ProductoUpdate",
        "ProductoPublic",
        "ProductoCategoriaCreate",
        "ProductoCategoriaPublic",
    ]:
        assert expected_schema in components, f"Falta {expected_schema} en components.schemas de OpenAPI"
