"""Pruebas de integración para repositorios y Unit of Work de Categorías y Productos (E3.2)."""

from collections.abc import Callable

import pytest
from sqlmodel import Session

from app.core.database import _build_engine, create_all_tables
from app.modules.categorias import (
    Categoria,
    CategoriaRead,
    CategoriaRepository,
    CategoriaUnitOfWork,
)
from app.modules.productos import (
    Producto,
    ProductoRead,
    ProductoRepository,
    ProductoUnitOfWork,
)


@pytest.fixture()
def session_factory() -> Callable[[], Session]:
    """Crea un motor SQLite en memoria aislado con tablas creadas para cada test."""
    engine = _build_engine("sqlite:///:memory:")
    create_all_tables(engine)
    return lambda: Session(engine, expire_on_commit=False)


def test_categoria_repository_get_by_nombre_list_y_get_activa(
    session_factory: Callable[[], Session],
) -> None:
    """Verifica get_by_nombre (incluyendo inactivas), list_activas y get_activa_by_id."""
    with CategoriaUnitOfWork(session_factory=session_factory) as uow:
        cat_act_1 = uow.categorias.add(Categoria(nombre="Bebidas", descripcion="Frías"))
        cat_inact = uow.categorias.add(Categoria(nombre="Postres", activo=False))
        cat_act_2 = uow.categorias.add(Categoria(nombre="Pizzas", descripcion="Artesanales"))
        assert cat_act_1.id is not None
        assert cat_inact.id is not None
        assert cat_act_2.id is not None
        inactiva_id = cat_inact.id
        activa_id = cat_act_1.id

    with Session(session_factory().bind, expire_on_commit=False) as session:
        repo = CategoriaRepository(session)
        # get_by_nombre incluye inactivas porque la baja lógica no libera el nombre único
        encontrada_inactiva = repo.get_by_nombre("Postres")
        assert encontrada_inactiva is not None
        assert encontrada_inactiva.id == inactiva_id
        assert encontrada_inactiva.activo is False

        assert repo.get_by_nombre("Inexistente") is None

        activas = repo.list_activas()
        assert [c.nombre for c in activas] == ["Bebidas", "Pizzas"]
        assert [c.nombre for c in repo.get_all_activas(skip=1, limit=1)] == ["Pizzas"]

        assert repo.get_activa_by_id(activa_id) is not None
        assert repo.get_activa_by_id(inactiva_id) is None


def test_categoria_uow_model_validate_commit_y_rollback(
    session_factory: Callable[[], Session],
) -> None:
    """Verifica CategoriaRead.model_validate dentro del with, commit y rollback ante error."""
    with CategoriaUnitOfWork(session_factory=session_factory) as uow:
        creada = uow.categorias.add(Categoria(nombre="Empanadas", descripcion="Salteñas"))
        dto = CategoriaRead.model_validate(creada)

    assert dto.id > 0
    assert dto.nombre == "Empanadas"
    assert dto.activo is True

    with pytest.raises(RuntimeError, match="Fallo simulado"):
        with CategoriaUnitOfWork(session_factory=session_factory) as uow:
            uow.categorias.add(Categoria(nombre="Hamburguesas"))
            raise RuntimeError("Fallo simulado")

    with CategoriaUnitOfWork(session_factory=session_factory) as uow:
        assert uow.categorias.get_by_nombre("Empanadas") is not None
        assert uow.categorias.get_by_nombre("Hamburguesas") is None


def test_producto_uow_sesion_compartida_y_rollback_conjunto(
    session_factory: Callable[[], Session],
) -> None:
    """Verifica que ProductoUnitOfWork comparte sesión y revierte ambos repos ante error."""
    with pytest.raises(ValueError, match="Error transaccional"):
        with ProductoUnitOfWork(session_factory=session_factory) as uow:
            assert uow.productos.session is uow.categorias.session
            cat = uow.categorias.add(Categoria(nombre="Minutas"))
            assert cat.id is not None
            uow.productos.add(
                Producto(
                    categoria_id=cat.id,
                    nombre="Milanesa",
                    precio_base=5500.0,
                    stock=10,
                    disponible=True,
                )
            )
            raise ValueError("Error transaccional")

    with ProductoUnitOfWork(session_factory=session_factory) as uow:
        assert uow.categorias.get_by_nombre("Minutas") is None
        items, total = uow.productos.search()
        assert items == []
        assert total == 0


def test_producto_repository_search_filtros_paginacion_y_model_validate(
    session_factory: Callable[[], Session],
) -> None:
    """Verifica search (case-insensitive, filtros, activos, paginación) y ProductoRead."""
    with ProductoUnitOfWork(session_factory=session_factory) as uow:
        cat_pizzas = uow.categorias.add(Categoria(nombre="Pizzas"))
        cat_bebidas = uow.categorias.add(Categoria(nombre="Bebidas"))
        assert cat_pizzas.id is not None
        assert cat_bebidas.id is not None

        p1 = uow.productos.add(
            Producto(
                categoria_id=cat_pizzas.id,
                nombre="Pizza Muzzarella",
                precio_base=8000.0,
                stock=12,
                disponible=True,
            )
        )
        p2 = uow.productos.add(
            Producto(
                categoria_id=cat_pizzas.id,
                nombre="Pizza Napolitana",
                precio_base=9000.0,
                stock=0,
                disponible=False,
            )
        )
        p3 = uow.productos.add(
            Producto(
                categoria_id=cat_bebidas.id,
                nombre="Cerveza Artesanal",
                precio_base=3500.0,
                stock=20,
                disponible=True,
            )
        )
        p_inactivo = uow.productos.add(
            Producto(
                categoria_id=cat_pizzas.id,
                nombre="Pizza Especial Inactiva",
                precio_base=9500.0,
                stock=5,
                disponible=True,
                activo=False,
            )
        )
        assert p1.id is not None and p2.id is not None and p3.id is not None
        assert p_inactivo.id is not None
        pizzas_id = cat_pizzas.id
        p1_id = p1.id
        p_inactivo_id = p_inactivo.id

    with ProductoUnitOfWork(session_factory=session_factory) as uow:
        assert isinstance(uow.productos, ProductoRepository)

        # Búsqueda case-insensitive por search y exclusión de activo=False
        items_pizza, total_pizza = uow.productos.search(search="pIzZa")
        assert total_pizza == 2
        assert [p.nombre for p in items_pizza] == [
            "Pizza Muzzarella",
            "Pizza Napolitana",
        ]

        # Alias nombre
        items_nombre, total_nombre = uow.productos.search(nombre="muzza")
        assert total_nombre == 1
        assert items_nombre[0].nombre == "Pizza Muzzarella"

        # Filtro por categoria_id y disponible=True
        items_disp, total_disp = uow.productos.search(
            categoria_id=pizzas_id,
            disponible=True,
        )
        assert total_disp == 1
        assert items_disp[0].nombre == "Pizza Muzzarella"

        # Paginación skip/limit con total exacto de activos
        page_items, page_total = uow.productos.search(skip=1, limit=1)
        assert page_total == 3
        assert len(page_items) == 1
        assert page_items[0].nombre == "Pizza Napolitana"

        # Validación de ProductoRead con categoria anidada dentro del bloque with
        dto = ProductoRead.model_validate(page_items[0])
        assert dto.categoria.nombre == "Pizzas"
        assert dto.disponible is False

        # get_by_id incluye inactivos con categoria; get_activo_by_id excluye inactivos
        prod_activo = uow.productos.get_activo_by_id(p1_id)
        assert prod_activo is not None
        assert ProductoRead.model_validate(prod_activo).categoria.nombre == "Pizzas"

        assert uow.productos.get_activo_by_id(p_inactivo_id) is None
        prod_inactivo = uow.productos.get_by_id(p_inactivo_id)
        assert prod_inactivo is not None
        assert prod_inactivo.categoria is not None
        assert prod_inactivo.categoria.nombre == "Pizzas"
