"""Pruebas automatizadas para semillado de unidades de medida, endpoint GET /api/v1/unidades-medida, CORS, Swagger y ciclo lifespan."""

import os
import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select, text

import app.core.database as db
from app.core.database import get_session
from app.core.seed import listar_unidades_medida, seed_unidades_medida
from app.main import app
from app.modules.unidades_medida.model import TipoUnidad, UnidadMedida, UnidadMedidaPublic


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
    """Crea un motor y sesión transaccional aislada para pruebas de unidades de medida."""
    url, is_pg = _resolve_test_engine()

    if is_pg:
        schema_name = f"e14_{uuid.uuid4().hex}"
        admin_engine = create_engine(url, echo=False)
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
            conn.commit()

        engine = create_engine(
            url,
            connect_args={"options": f"-csearch_path={schema_name}"},
            echo=False,
        )
        SQLModel.metadata.create_all(engine, tables=[UnidadMedida.__table__])

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

        SQLModel.metadata.create_all(engine, tables=[UnidadMedida.__table__])
        with Session(engine) as session:
            yield session
        engine.dispose()


# Consigna: docs/consignas_examen_2.md, 4/R1 y CI Fase D — seed idempotente y verificación de catálogo.
def test_seed_unidades_medida_idempotente(session_fixture: Session, monkeypatch: pytest.MonkeyPatch):
    """Verifica que el seed inicial inserte exactamente las 6 unidades obligatorias y sea idempotente."""
    # Pasada 1: tabla vacía
    unidades_p1 = seed_unidades_medida(session_fixture)
    assert len(unidades_p1) == 6

    simbolos_obtenidos = [u.simbolo for u in unidades_p1]
    nombres_obtenidos = [u.nombre for u in unidades_p1]
    tipos_obtenidos = [u.tipo for u in unidades_p1]

    assert simbolos_obtenidos == ["kg", "g", "L", "mL", "u", "doc"]
    assert nombres_obtenidos == [
        "kilogramo",
        "gramo",
        "litro",
        "mililitro",
        "pieza",
        "docena",
    ]
    assert tipos_obtenidos == [
        TipoUnidad.peso,
        TipoUnidad.peso,
        TipoUnidad.volumen,
        TipoUnidad.volumen,
        TipoUnidad.contable,
        TipoUnidad.contable,
    ]

    # Pasada 2: segunda ejecución sobre la misma sesión
    unidades_p2 = seed_unidades_medida(session_fixture)
    assert len(unidades_p2) == 6

    # Consulta directa para verificar que no hay duplicados en la base de datos
    filas = session_fixture.exec(select(UnidadMedida)).all()
    assert len(filas) == 6

    # Verificación de ejecución sin argumentos delegando a session_fixture.bind
    monkeypatch.setattr(db, "engine", session_fixture.bind)
    unidades_p3 = seed_unidades_medida()
    assert len(unidades_p3) == 6


# Consigna: docs/consignas_examen_2.md, 4/R1 — "El seed solo inserta si la tabla está vacía".
def test_seed_no_inserta_si_tabla_no_esta_vacia(session_fixture: Session):
    """Verifica que si la tabla ya contiene al menos un registro, el seed no inserta nuevas filas."""
    unidad_previa = UnidadMedida(nombre="metro", simbolo="m", tipo=TipoUnidad.contable)
    session_fixture.add(unidad_previa)
    session_fixture.commit()

    resultado = seed_unidades_medida(session_fixture)
    assert len(resultado) == 1
    assert resultado[0].simbolo == "m"

    filas = session_fixture.exec(select(UnidadMedida)).all()
    assert len(filas) == 1
    assert filas[0].nombre == "metro"


# Consigna: docs/consignas_examen_2.md, 4/R1, 4/R2 y 6.1 — GET /api/v1/unidades-medida HTTP 200 y schema response_model.
def test_get_unidades_medida_endpoint(session_fixture: Session):
    """Verifica el endpoint GET /api/v1/unidades-medida con inyección de sesión y contrato UnidadMedidaPublic."""
    seed_unidades_medida(session_fixture)

    def override_get_session():
        yield session_fixture

    app.dependency_overrides[get_session] = override_get_session
    try:
        client = TestClient(app)
        response = client.get("/api/v1/unidades-medida")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 6

        # Validar contrato exacto contra schema Pydantic/SQLModel
        for item in data:
            validado = UnidadMedidaPublic(**item)
            assert set(item.keys()) == {"id", "nombre", "simbolo", "tipo"}
            assert validado.id is not None
            assert validado.nombre in {"kilogramo", "gramo", "litro", "mililitro", "pieza", "docena"}
            assert validado.simbolo in {"kg", "g", "L", "mL", "u", "doc"}
            assert validado.tipo in {TipoUnidad.peso, TipoUnidad.volumen, TipoUnidad.contable}

        # Validar orden determinista por id
        ids = [item["id"] for item in data]
        assert ids == sorted(ids)
    finally:
        app.dependency_overrides.clear()


# Consigna: docs/consignas_examen_2.md, 4/R1 — CORS habilitado con CORSMiddleware para el origen del frontend (E1.5).
def test_cors_middleware_habilitado_para_frontend(session_fixture: Session):
    """Verifica que CORSMiddleware responda preflight OPTIONS y GET con los encabezados adecuados."""
    seed_unidades_medida(session_fixture)

    def override_get_session():
        yield session_fixture

    app.dependency_overrides[get_session] = override_get_session
    try:
        client = TestClient(app)

        # 1. Preflight OPTIONS desde localhost:5173
        preflight = client.options(
            "/api/v1/unidades-medida",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert preflight.headers.get("access-control-allow-credentials") == "true"
        allow_methods = preflight.headers.get("access-control-allow-methods", "")
        assert "GET" in allow_methods

        # 2. GET regular desde 127.0.0.1:5173
        response_ip = client.get(
            "/api/v1/unidades-medida",
            headers={"Origin": "http://127.0.0.1:5173"},
        )
        assert response_ip.status_code == 200
        assert response_ip.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
        assert response_ip.headers.get("access-control-allow-credentials") == "true"

        # 3. Origen no autorizado no debe recibir access-control-allow-origin
        response_denied = client.get(
            "/api/v1/unidades-medida",
            headers={"Origin": "http://evil-attacker.com"},
        )
        assert response_denied.status_code == 200
        assert response_denied.headers.get("access-control-allow-origin") is None
    finally:
        app.dependency_overrides.clear()


# Consigna: docs/consignas_examen_2.md, 4/R1 — Swagger operativo en /docs con todos los endpoints documentados (E1.5).
def test_swagger_docs_y_openapi_operativos():
    """Verifica que la documentación OpenAPI/Swagger (/docs y /openapi.json) esté disponible y documente los endpoints."""
    client = TestClient(app)

    # 1. /docs debe responder 200 HTML con Swagger UI
    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
    assert "text/html" in res_docs.headers.get("content-type", "")
    assert "swagger-ui" in res_docs.text.lower() or "Swagger UI" in res_docs.text

    # 2. /openapi.json debe responder 200 JSON con el esquema del catálogo
    res_openapi = client.get("/openapi.json")
    assert res_openapi.status_code == 200
    openapi_data = res_openapi.json()
    assert openapi_data["info"]["title"] == "Food Store — Catálogo de Productos API"
    assert "/api/v1/unidades-medida" in openapi_data["paths"]
    assert "get" in openapi_data["paths"]["/api/v1/unidades-medida"]
    assert "UnidadMedidaPublic" in openapi_data.get("components", {}).get("schemas", {})

    # 3. Tags configurados deben estar presentes
    tag_names = {tag["name"] for tag in openapi_data.get("tags", [])}
    assert {"Unidades de Medida", "Categorías", "Productos"}.issubset(tag_names)


# Consigna: docs/consignas_examen_2.md, 4/R1 y Sección 6.1 — Ciclo de vida lifespan (create_db_and_tables + seed) (E1.5).
def test_lifespan_ejecuta_ddl_y_seed(session_fixture: Session, monkeypatch: pytest.MonkeyPatch):
    """Verifica que el contextmanager lifespan ejecute el DDL y el semillado al arrancar la app."""
    ddl_called = []
    seed_called = []

    def mock_create_db():
        ddl_called.append(True)
        SQLModel.metadata.create_all(session_fixture.bind)

    def mock_seed():
        seed_called.append(True)
        return seed_unidades_medida(session_fixture)

    monkeypatch.setattr("app.main.create_db_and_tables", mock_create_db)
    monkeypatch.setattr("app.main.seed_unidades_medida", mock_seed)

    def override_get_session():
        yield session_fixture

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as client:
            assert len(ddl_called) == 1
            assert len(seed_called) == 1
            response = client.get("/api/v1/unidades-medida")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 6
            simbolos = [item["simbolo"] for item in data]
            assert set(simbolos) == {"kg", "g", "L", "mL", "u", "doc"}
    finally:
        app.dependency_overrides.clear()
