"""Pruebas unitarias e integración para el seed idempotente TPI (E1.3 / CE-04)."""

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect
from sqlmodel import Session, select

from app.core.database import _build_engine
from app.core.security import verify_password
from app.db.seed import ADMIN_PASSWORD, ADMIN_USERNAME, seed
from app.modules.categorias.models import Categoria
from app.modules.productos.models import Producto
from app.modules.usuarios.models import Usuario

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_seed_inicializa_bd_limpia_y_cumple_contrato_ce04() -> None:
    """seed(engine) crea tablas en BD vacía y carga admin, >=3 categorías y >=8 productos."""
    test_engine = _build_engine("sqlite:///:memory:")
    try:
        resumen = seed(test_engine)
        assert resumen["usuarios"] == 1
        assert resumen["categorias"] >= 3
        assert resumen["productos"] >= 8

        tablas = set(inspect(test_engine).get_table_names())
        assert {
            "usuarios",
            "categorias",
            "productos",
            "pedidos",
            "detalle_pedidos",
        }.issubset(tablas)

        with Session(test_engine) as session:
            admin = session.exec(
                select(Usuario).where(Usuario.username == ADMIN_USERNAME)
            ).first()
            assert admin is not None
            assert admin.role == "admin"
            assert admin.disabled is False
            assert verify_password(ADMIN_PASSWORD, admin.hashed_password) is True

            categorias = list(
                session.exec(
                    select(Categoria).where(Categoria.activo == True)  # noqa: E712
                ).all()
            )
            assert len(categorias) >= 3

            productos = list(
                session.exec(
                    select(Producto).where(
                        Producto.activo == True,  # noqa: E712
                        Producto.disponible == True,  # noqa: E712
                        Producto.stock > 0,
                    )
                ).all()
            )
            assert len(productos) >= 8
            assert all(p.categoria_id is not None for p in productos)
            assert all(
                p.imagen_url is not None
                and p.imagen_url.startswith("/img/")
                and p.imagen_url.endswith(".jpg")
                for p in productos
            )
    finally:
        test_engine.dispose()


def test_seed_es_estrictamente_idempotente_con_engine_y_session() -> None:
    """Ejecutar seed N veces (con Engine y Session como en CI) no duplica registros."""
    test_engine = _build_engine("sqlite:///:memory:")
    try:
        primero = seed(test_engine)
        segundo = seed(test_engine)
        with Session(test_engine) as session:
            tercero = seed(session)

        assert primero["usuarios"] == 1
        assert segundo == {"usuarios": 0, "categorias": 0, "productos": 0}
        assert tercero == {"usuarios": 0, "categorias": 0, "productos": 0}

        with Session(test_engine) as session:
            usuarios = list(session.exec(select(Usuario)).all())
            categorias = list(session.exec(select(Categoria)).all())
            productos = list(session.exec(select(Producto)).all())

            assert len(usuarios) == 1
            assert len(categorias) == primero["categorias"]
            assert len(productos) == primero["productos"]
    finally:
        test_engine.dispose()


def test_seed_cli_python_m_app_db_seed_idempotente(tmp_path: Path) -> None:
    """python -m app.db.seed corre directamente en BD limpia y es idempotente."""
    db_file = tmp_path / "seed_cli_test.db"
    db_url = f"sqlite:///{db_file}"
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url

    proc1 = subprocess.run(
        [sys.executable, "-m", "app.db.seed"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc1.returncode == 0, proc1.stderr

    proc2 = subprocess.run(
        [sys.executable, "-m", "app.db.seed"],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc2.returncode == 0, proc2.stderr

    verify_engine = _build_engine(db_url)
    try:
        with Session(verify_engine) as session:
            usuarios = list(session.exec(select(Usuario)).all())
            categorias = list(session.exec(select(Categoria)).all())
            productos = list(session.exec(select(Producto)).all())

            assert len(usuarios) == 1
            assert usuarios[0].username == ADMIN_USERNAME
            assert usuarios[0].role == "admin"
            assert len(categorias) >= 3
            assert len(productos) >= 8
            assert all(p.stock > 0 and p.disponible and p.activo for p in productos)
    finally:
        verify_engine.dispose()


def test_seed_migra_idempotentemente_urls_cdn_legacy() -> None:
    """Si existen productos con el placeholder CDN legacy, seed() los migra a /img/ sin duplicar."""
    test_engine = _build_engine("sqlite:///:memory:")
    try:
        primero = seed(test_engine)
        with Session(test_engine) as session:
            clasica = session.exec(
                select(Producto).where(Producto.nombre == "Hamburguesa Clásica")
            ).first()
            assert clasica is not None
            clasica.imagen_url = "https://cdn.foodstore.local/img/hamburguesa-clasica.jpg"
            session.commit()

        segundo = seed(test_engine)
        assert segundo == {"usuarios": 0, "categorias": 0, "productos": 0}

        with Session(test_engine) as session:
            productos = list(session.exec(select(Producto)).all())
            assert len(productos) == primero["productos"]
            clasica_actualizada = session.exec(
                select(Producto).where(Producto.nombre == "Hamburguesa Clásica")
            ).first()
            assert clasica_actualizada is not None
            assert clasica_actualizada.imagen_url == "/img/hamburguesa-clasica.jpg"
    finally:
        test_engine.dispose()
