"""Pruebas unitarias y de integración para app/core/database.py, app/core/__init__.py y app/main.py (E1.2)."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, Session, SQLModel

from app.core import (
    DATABASE_URL,
    SessionDep,
    Settings,
    create_all_tables,
    create_db_and_tables,
    engine,
    get_session,
    get_settings,
    session_factory,
    settings,
)
from app.core.database import BACKEND_DIR, _build_engine, normalize_database_url
from app.main import API_V1_PREFIX, CORS_ORIGINS, app
from app.modules.categorias.router import router as categorias_router
from app.modules.productos.router import router as productos_router


def test_core_reexports_y_settings_database_url() -> None:
    """Verifica reexportaciones en app.core y consumo de settings.DATABASE_URL."""
    assert callable(create_all_tables)
    assert callable(create_db_and_tables)
    assert callable(session_factory)
    assert callable(get_session)
    assert callable(get_settings)
    assert isinstance(settings, Settings)
    assert SessionDep is not None
    assert engine is not None
    assert DATABASE_URL == normalize_database_url(settings.DATABASE_URL)


def test_normalize_database_url() -> None:
    """Verifica normalización de postgres://, postgresql:// y sqlite:///./..."""
    assert (
        normalize_database_url("postgres://user:pass@localhost:5432/db")
        == "postgresql+psycopg2://user:pass@localhost:5432/db"
    )
    assert (
        normalize_database_url("postgresql://user:pass@localhost:5432/db")
        == "postgresql+psycopg2://user:pass@localhost:5432/db"
    )
    expected_sqlite = f"sqlite:///{(BACKEND_DIR / 'data/test.db').resolve()}"
    assert normalize_database_url("sqlite:///./data/test.db") == expected_sqlite
    assert normalize_database_url("sqlite:///:memory:") == "sqlite:///:memory:"
    assert normalize_database_url("sqlite://") == "sqlite://"


def test_build_engine_static_pool_y_sqlite_pragmas(tmp_path: Path) -> None:
    """Verifica StaticPool en memoria y listener PRAGMA foreign_keys=ON + char_length."""
    mem_engine = _build_engine("sqlite:///:memory:")
    bare_engine = _build_engine("sqlite://")
    file_engine = _build_engine(f"sqlite:///{tmp_path / 'file.db'}")

    try:
        assert isinstance(mem_engine.pool, StaticPool)
        assert isinstance(bare_engine.pool, StaticPool)
        assert not isinstance(file_engine.pool, StaticPool)
        assert file_engine.pool._pre_ping is True

        with mem_engine.connect() as conn:
            fk_enabled = conn.execute(text("PRAGMA foreign_keys")).scalar_one()
            char_len = conn.execute(text("SELECT char_length('FoodStore')")).scalar_one()
            assert fk_enabled == 1
            assert char_len == 9
    finally:
        mem_engine.dispose()
        bare_engine.dispose()
        file_engine.dispose()


def test_session_factory_expire_on_commit_false_y_get_session() -> None:
    """Verifica session_factory() con expire_on_commit=False y cierre en get_session()."""
    with session_factory() as session:
        assert isinstance(session, Session)
        assert session.expire_on_commit is False

    gen = get_session()
    dep_session = next(gen)
    try:
        assert isinstance(dep_session, Session)
        assert dep_session.expire_on_commit is False
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_create_all_tables_en_motor_destino() -> None:
    """Verifica create_all_tables(target_engine) creando una tabla SQLModel temporal."""

    class _DummyE12Table(SQLModel, table=True):
        __tablename__ = "_dummy_e12_table"
        id: int | None = Field(default=None, primary_key=True)
        nombre: str

    test_engine = _build_engine("sqlite:///:memory:")
    try:
        create_all_tables(test_engine)
        with Session(test_engine, expire_on_commit=False) as session:
            item = _DummyE12Table(nombre="Prueba")
            session.add(item)
            session.commit()
            assert item.id is not None
            assert item.nombre == "Prueba"
    finally:
        SQLModel.metadata.remove(_DummyE12Table.__table__)
        test_engine.dispose()


def test_main_lifespan_health_docs_prefijos_y_cors(monkeypatch) -> None:
    """Verifica lifespan, /api/v1/health, /docs, /redoc, /openapi.json, prefijos y CORS."""
    lifespan_calls: list[str] = []

    def _fake_create_all_tables() -> None:
        lifespan_calls.append("called")

    monkeypatch.setattr("app.main.create_all_tables", _fake_create_all_tables)

    assert API_V1_PREFIX == "/api/v1"
    assert CORS_ORIGINS == [settings.FRONTEND_ORIGIN]
    assert "*" not in CORS_ORIGINS
    assert categorias_router.prefix == "/categorias"
    assert productos_router.prefix == "/productos"

    with TestClient(app) as client:
        assert lifespan_calls == ["called"]

        health_res = client.get(
            "/api/v1/health",
            headers={"Origin": settings.FRONTEND_ORIGIN},
        )
        assert health_res.status_code == 200
        assert health_res.json() == {"status": "ok"}
        assert health_res.headers.get("access-control-allow-origin") == settings.FRONTEND_ORIGIN
        assert health_res.headers.get("access-control-allow-credentials") == "true"

        preflight_res = client.options(
            "/api/v1/health",
            headers={
                "Origin": settings.FRONTEND_ORIGIN,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert preflight_res.status_code == 200
        assert preflight_res.headers.get("access-control-allow-origin") == settings.FRONTEND_ORIGIN
        assert preflight_res.headers.get("access-control-allow-credentials") == "true"

        docs_res = client.get("/docs")
        assert docs_res.status_code == 200

        redoc_res = client.get("/redoc")
        assert redoc_res.status_code == 200

        openapi_res = client.get("/openapi.json")
        assert openapi_res.status_code == 200
        openapi_data = openapi_res.json()
        assert "/api/v1/health" in openapi_data["paths"]
        assert "get" in openapi_data["paths"]["/api/v1/health"]
