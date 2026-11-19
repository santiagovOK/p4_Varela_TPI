"""Pruebas unitarias de schemas SQLModel para Productos (E2.1)."""

import pytest
from pydantic import ValidationError

from app.modules.categorias.models import Categoria
from app.modules.productos import (
    Producto,
    ProductoCreate,
    ProductoRead,
    ProductoStockUpdate,
    ProductoUpdate,
    ProductosPaginados,
)


def test_producto_create_defaults_y_restricciones() -> None:
    """Valida defaults y restricciones de ProductoCreate."""
    p = ProductoCreate(nombre="Muzzarella", precio_base=8000.0, categoria_id=1)
    assert p.descripcion is None
    assert p.imagen_url is None
    assert p.stock == 0
    assert p.disponible is True

    with pytest.raises(ValidationError):
        ProductoCreate(nombre="", precio_base=100.0, categoria_id=1)

    with pytest.raises(ValidationError):
        ProductoCreate(nombre="Pizza", precio_base=-1.0, categoria_id=1)

    with pytest.raises(ValidationError):
        ProductoCreate(nombre="Pizza", precio_base=100.0, stock=-1, categoria_id=1)

    with pytest.raises(ValidationError):
        ProductoCreate(nombre="Pizza", precio_base=100.0, categoria_id=0)


def test_producto_update_parcial_y_restricciones() -> None:
    """Valida ProductoUpdate parcial con restricciones preservadas."""
    empty = ProductoUpdate()
    assert empty.model_dump(exclude_unset=True) == {}

    partial = ProductoUpdate(precio_base=9200.0, stock=5)
    assert partial.model_dump(exclude_unset=True) == {
        "precio_base": 9200.0,
        "stock": 5,
    }

    with pytest.raises(ValidationError):
        ProductoUpdate(nombre="")

    with pytest.raises(ValidationError):
        ProductoUpdate(precio_base=-0.01)

    with pytest.raises(ValidationError):
        ProductoUpdate(stock=-5)

    with pytest.raises(ValidationError):
        ProductoUpdate(categoria_id=0)


def test_producto_read_stock_update_y_paginados() -> None:
    """Valida ProductoRead con CategoriaRead anidada, ProductoStockUpdate y ProductosPaginados."""
    cat = Categoria(id=2, nombre="Empanadas", descripcion="Al horno", activo=True)
    prod = Producto(
        id=10,
        categoria_id=2,
        nombre="Empanada de Carne",
        descripcion="Cortada a cuchillo",
        precio_base=1200.0,
        imagen_url=None,
        stock=24,
        disponible=True,
        activo=True,
        categoria=cat,
    )

    read_dto = ProductoRead.model_validate(prod)
    assert read_dto.id == 10
    assert read_dto.categoria.id == 2
    assert read_dto.categoria.nombre == "Empanadas"

    stock_dto = ProductoStockUpdate(stock=0, disponible=False)
    assert stock_dto.stock == 0
    assert stock_dto.disponible is False

    with pytest.raises(ValidationError):
        ProductoStockUpdate(stock=-1, disponible=True)

    paginados = ProductosPaginados(total=1, items=[read_dto])
    assert paginados.total == 1
    assert len(paginados.items) == 1
    assert paginados.items[0].nombre == "Empanada de Carne"
