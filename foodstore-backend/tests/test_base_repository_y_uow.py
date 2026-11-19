"""Pruebas unitarias y de integración para BaseRepository[T] y UnitOfWork (E3.1)."""

import pytest
from sqlmodel import Session

from app.core import BaseRepository, ModelType, UnitOfWork, UnitOfWorkBase
from app.core.database import _build_engine, create_all_tables
from app.modules.categorias.models import Categoria
from app.modules.productos.models import Producto
from app.modules.productos.schemas import ProductoRead


class SessionDouble:
    """Doble de pruebas para verificar el ciclo transaccional de UnitOfWork."""

    def __init__(self, *, fail_on_commit: bool = False) -> None:
        self.fail_on_commit = fail_on_commit
        self.expire_on_commit = True
        self.committed = False
        self.rolled_back = False
        self.closed = False
        self.calls: list[str] = []

    def commit(self) -> None:
        self.calls.append("commit")
        if self.fail_on_commit:
            raise RuntimeError("Error simulado al confirmar")
        self.committed = True

    def rollback(self) -> None:
        self.calls.append("rollback")
        self.rolled_back = True

    def close(self) -> None:
        self.calls.append("close")
        self.closed = True


class FailingInitUoW(UnitOfWork):
    """Subclase de prueba que falla durante _init_repositories."""

    def _init_repositories(self, session: Session) -> None:
        raise RuntimeError("Fallo al inicializar repositorios")


def test_core_reexports_y_alias_e31() -> None:
    """Verifica reexportaciones en app.core y alias compatibles."""
    assert BaseRepository is not None
    assert ModelType is not None
    assert UnitOfWorkBase is UnitOfWork


def test_uow_commit_y_close_sin_excepcion() -> None:
    """Sin excepción en el bloque with, UnitOfWork ejecuta commit y close."""
    session_double = SessionDouble()
    uow = UnitOfWork(session_factory=lambda: session_double)  # type: ignore[arg-type, return-value]

    with uow as active_uow:
        assert active_uow.session is session_double
        assert session_double.expire_on_commit is False

    assert session_double.committed is True
    assert session_double.rolled_back is False
    assert session_double.closed is True
    assert session_double.calls == ["commit", "close"]
    assert uow.session is None


def test_uow_rollback_y_close_con_excepcion() -> None:
    """Ante excepción en el bloque with, UnitOfWork ejecuta rollback y close."""
    session_double = SessionDouble()
    uow = UnitOfWork(session_factory=lambda: session_double)  # type: ignore[arg-type, return-value]

    with pytest.raises(ValueError, match="Fallo de negocio"):
        with uow:
            raise ValueError("Fallo de negocio")

    assert session_double.committed is False
    assert session_double.rolled_back is True
    assert session_double.closed is True
    assert session_double.calls == ["rollback", "close"]
    assert uow.session is None


def test_uow_rollback_y_close_cuando_falla_commit() -> None:
    """Si commit() falla al salir, UnitOfWork revierte, cierra y relanza."""
    session_double = SessionDouble(fail_on_commit=True)
    uow = UnitOfWork(session_factory=lambda: session_double)  # type: ignore[arg-type, return-value]

    with pytest.raises(RuntimeError, match="Error simulado al confirmar"):
        with uow:
            pass

    assert session_double.committed is False
    assert session_double.rolled_back is True
    assert session_double.closed is True
    assert session_double.calls == ["commit", "rollback", "close"]
    assert uow.session is None


def test_uow_close_cuando_falla_init_repositories() -> None:
    """Si _init_repositories falla, UnitOfWork cierra la sesión y la limpia."""
    session_double = SessionDouble()
    uow = FailingInitUoW(session_factory=lambda: session_double)  # type: ignore[arg-type, return-value]

    with pytest.raises(RuntimeError, match="Fallo al inicializar repositorios"):
        with uow:
            pass

    assert session_double.committed is False
    assert session_double.rolled_back is False
    assert session_double.closed is True
    assert session_double.calls == ["close"]
    assert uow.session is None


def test_uow_commit_y_rollback_manual_sin_sesion_activa() -> None:
    """Llamar a commit() o rollback() fuera de __enter__ lanza RuntimeError."""
    uow = UnitOfWork(session_factory=lambda: SessionDouble())  # type: ignore[arg-type, return-value]

    with pytest.raises(RuntimeError, match="sesión activa"):
        uow.commit()
    with pytest.raises(RuntimeError, match="sesión activa"):
        uow.rollback()

    with uow:
        pass

    with pytest.raises(RuntimeError, match="sesión activa"):
        uow.commit()
    with pytest.raises(RuntimeError, match="sesión activa"):
        uow.rollback()


def test_uow_por_defecto_abre_sesion_con_expire_on_commit_false() -> None:
    """UnitOfWork() por defecto abre una sesión SQLModel con expire_on_commit=False."""
    with UnitOfWork() as uow:
        assert isinstance(uow.session, Session)
        assert uow.session.expire_on_commit is False


def test_base_repository_crud_completo_en_sqlite_memoria() -> None:
    """Verifica add/create/update, get_by_id, get_all (skip/limit) y delete."""
    eng = _build_engine("sqlite:///:memory:")
    create_all_tables(eng)

    def memory_session_factory() -> Session:
        return Session(eng, expire_on_commit=False)

    with UnitOfWork(session_factory=memory_session_factory) as uow:
        assert uow.session is not None
        repo = BaseRepository(uow.session, Categoria)

        c1 = repo.add(Categoria(nombre="Empanadas", descripcion="Al horno"))
        c2 = repo.create(Categoria(nombre="Pizzas", descripcion="A la piedra"))
        c3 = repo.add(Categoria(nombre="Bebidas", descripcion="Sin alcohol"))

        assert c1.id is not None
        assert c2.id is not None
        assert c3.id is not None

        encontrada = repo.get_by_id(c1.id)
        assert encontrada is not None
        assert encontrada.nombre == "Empanadas"

        c1.descripcion = "Al horno de barro"
        repo.update(c1)

        todas = repo.get_all()
        assert len(todas) == 3

        paginadas = repo.get_all(skip=1, limit=1)
        assert len(paginadas) == 1
        assert paginadas[0].id == c2.id

        paginadas_offset = repo.get_all(offset=2, limit=1)
        assert len(paginadas_offset) == 1
        assert paginadas_offset[0].id == c3.id

        repo.delete(c3)
        assert repo.get_by_id(c3.id) is None

    with UnitOfWork(session_factory=memory_session_factory) as uow_check:
        assert uow_check.session is not None
        repo_check = BaseRepository(uow_check.session, Categoria)
        restantes = repo_check.get_all()
        assert [c.nombre for c in restantes] == ["Empanadas", "Pizzas"]
        assert restantes[0].descripcion == "Al horno de barro"


def test_uow_rollback_real_en_sqlite_no_persiste_datos() -> None:
    """Verifica rollback real en SQLite cuando ocurre una excepción en el bloque with."""
    eng = _build_engine("sqlite:///:memory:")
    create_all_tables(eng)

    def memory_session_factory() -> Session:
        return Session(eng, expire_on_commit=False)

    with pytest.raises(RuntimeError, match="Abortar transacción"):
        with UnitOfWork(session_factory=memory_session_factory) as uow:
            assert uow.session is not None
            repo = BaseRepository(uow.session, Categoria)
            repo.add(Categoria(nombre="Postres", descripcion="Caseros"))
            raise RuntimeError("Abortar transacción")

    with UnitOfWork(session_factory=memory_session_factory) as uow_check:
        assert uow_check.session is not None
        repo_check = BaseRepository(uow_check.session, Categoria)
        assert repo_check.get_all() == []


def test_model_validate_con_relacion_y_acceso_post_commit() -> None:
    """Valida ProductoRead con relación categoria dentro del with y acceso post-commit."""
    eng = _build_engine("sqlite:///:memory:")
    create_all_tables(eng)

    def memory_session_factory() -> Session:
        return Session(eng, expire_on_commit=False)

    with UnitOfWork(session_factory=memory_session_factory) as uow:
        assert uow.session is not None
        cat_repo = BaseRepository(uow.session, Categoria)
        prod_repo = BaseRepository(uow.session, Producto)

        categoria = cat_repo.add(Categoria(nombre="Hamburguesas", descripcion="Caseras"))
        assert categoria.id is not None

        producto = prod_repo.add(
            Producto(
                categoria_id=categoria.id,
                nombre="Doble Cheddar",
                descripcion="Con papas",
                precio_base=8500.0,
                stock=10,
            )
        )
        dto = ProductoRead.model_validate(producto)

    # Acceso post-commit sin DetachedInstanceError gracias a expire_on_commit=False.
    assert dto.id is not None
    assert dto.nombre == "Doble Cheddar"
    assert dto.categoria.nombre == "Hamburguesas"
    assert producto.nombre == "Doble Cheddar"
    assert producto.precio_base == 8500.0
