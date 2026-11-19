"""Pruebas unitarias de schemas SQLModel para Categorías (E2.1)."""

import pytest
from pydantic import ValidationError

from app.modules.categorias import (
    Categoria,
    CategoriaCreate,
    CategoriaRead,
    CategoriaUpdate,
)


def test_categoria_create_valido_y_restricciones() -> None:
    """Valida creación con límites de longitud en nombre y descripción opcional."""
    c1 = CategoriaCreate(nombre="Pizzas")
    assert c1.nombre == "Pizzas"
    assert c1.descripcion is None

    c2 = CategoriaCreate(nombre="AB", descripcion="Categoría mínima")
    assert c2.nombre == "AB"
    assert c2.descripcion == "Categoría mínima"

    with pytest.raises(ValidationError):
        CategoriaCreate(nombre="A")

    with pytest.raises(ValidationError):
        CategoriaCreate(nombre="X" * 101)


def test_categoria_update_parcial() -> None:
    """Valida actualización parcial PUT con todos los campos opcionales."""
    empty_upd = CategoriaUpdate()
    assert empty_upd.nombre is None
    assert empty_upd.descripcion is None
    assert empty_upd.model_dump(exclude_unset=True) == {}

    partial_upd = CategoriaUpdate(descripcion="Nueva descripción")
    assert partial_upd.model_dump(exclude_unset=True) == {
        "descripcion": "Nueva descripción"
    }

    with pytest.raises(ValidationError):
        CategoriaUpdate(nombre="A")

    with pytest.raises(ValidationError):
        CategoriaUpdate(nombre="X" * 101)


def test_categoria_read_y_reexports() -> None:
    """Valida DTO CategoriaRead y reexportación desde app.modules.categorias."""
    cat = Categoria(id=1, nombre="Postres", descripcion=None, activo=True)
    dto = CategoriaRead.model_validate(cat)
    assert dto.id == 1
    assert dto.nombre == "Postres"
    assert dto.descripcion is None
    assert dto.activo is True
