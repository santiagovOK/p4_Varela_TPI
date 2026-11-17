"""Pruebas unitarias para schemas Pydantic y validaciones declarativas de Categoria.

Consigna: docs/consignas_examen_2.md, 3.1, 3.4/RN-01, 4/R2, 4/R3 y 6.1.
Verifica contratos de entrada y salida (CategoriaBase, CategoriaCreate, CategoriaUpdate, CategoriaPublic),
validaciones declarativas de longitud mínima en nombre (RN-01) y serialización desde el modelo ORM.
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlmodel import SQLModel

# Registro preventivo de modelos para permitir instanciación de Categoria ORM sin base de datos activa.
import app.modules.productos.model  # noqa: F401
import app.modules.unidades_medida.model  # noqa: F401
from app.modules.categorias.model import Categoria
from app.modules.categorias.schema import (
    CategoriaBase,
    CategoriaCreate,
    CategoriaPublic,
    CategoriaUpdate,
)


def test_categoria_create_validos() -> None:
    """Verifica que CategoriaCreate acepte nombres válidos con longitud >= 3 y descripción opcional."""
    # Nombre exacto de 3 caracteres y descripción por defecto (None)
    dto_min = CategoriaCreate(nombre="Beb")
    assert dto_min.nombre == "Beb"
    assert dto_min.descripcion is None
    assert dto_min.model_dump() == {"nombre": "Beb", "descripcion": None}

    # Nombre extenso con descripción explícita
    dto_full = CategoriaCreate(
        nombre="Pastas Frescas",
        descripcion="Pastas artesanales de trigo candeal y rellenas",
    )
    assert dto_full.nombre == "Pastas Frescas"
    assert dto_full.descripcion == "Pastas artesanales de trigo candeal y rellenas"


def test_categoria_update_validos() -> None:
    """Verifica que CategoriaUpdate acepte nombres válidos con longitud >= 3 y soporte reemplazo de campos."""
    dto_update = CategoriaUpdate(
        nombre="Carnes Rojas",
        descripcion="Cortes vacunos envasados al vacío",
    )
    assert dto_update.nombre == "Carnes Rojas"
    assert dto_update.descripcion == "Cortes vacunos envasados al vacío"
    assert dto_update.model_dump() == {
        "nombre": "Carnes Rojas",
        "descripcion": "Cortes vacunos envasados al vacío",
    }

    # Descripción seteada a None explícitamente para limpiar la previa
    dto_clear_desc = CategoriaUpdate(nombre="Verduras", descripcion=None)
    assert dto_clear_desc.descripcion is None


@pytest.mark.parametrize("nombre_invalido", ["", "a", "ab", "  "])
def test_categoria_create_nombre_longitud_menor_a_tres_lanza_validation_error(
    nombre_invalido: str,
) -> None:
    """Consigna: docs/consignas_examen_2.md, 3.4/RN-01 — nombre < 3 caracteres debe ser rechazado."""
    with pytest.raises(ValidationError) as exc_info:
        CategoriaCreate(nombre=nombre_invalido)

    errores = exc_info.value.errors()
    assert any(err["loc"] == ("nombre",) for err in errores)
    assert any(
        "string_too_short" in err["type"] or "at least 3 characters" in err["msg"]
        for err in errores
    )


def test_categoria_create_nombre_requerido() -> None:
    """Verifica que omitir el campo nombre o pasarlo nulo lance ValidationError."""
    with pytest.raises(ValidationError):
        CategoriaCreate.model_validate({})

    with pytest.raises(ValidationError):
        CategoriaCreate.model_validate({"nombre": None})


@pytest.mark.parametrize("nombre_invalido", ["", "x", "xy"])
def test_categoria_update_nombre_invalido_lanza_validation_error(
    nombre_invalido: str,
) -> None:
    """Consigna: docs/consignas_examen_2.md, 4/R3 — PUT categorias/{id} aplica mismas validaciones que Create."""
    with pytest.raises(ValidationError) as exc_info:
        CategoriaUpdate(nombre=nombre_invalido)

    errores = exc_info.value.errors()
    assert any(err["loc"] == ("nombre",) for err in errores)


def test_categoria_public_model_validate_desde_orm_activo_y_anulado() -> None:
    """Consigna: docs/consignas_examen_2.md, 4/R3 y 6.1 — response_model CategoriaPublic desde entidad ORM."""
    # Instancia ORM activa sin fecha de anulación
    categoria_activa = Categoria(
        id=1,
        nombre="Postres",
        descripcion="Dulces y repostería artesanal",
        activo=True,
        anulado_at=None,
    )
    public_activa = CategoriaPublic.model_validate(categoria_activa)
    assert public_activa.id == 1
    assert public_activa.nombre == "Postres"
    assert public_activa.descripcion == "Dulces y repostería artesanal"
    assert public_activa.activo is True
    assert public_activa.anulado_at is None
    assert public_activa.model_dump() == {
        "id": 1,
        "nombre": "Postres",
        "descripcion": "Dulces y repostería artesanal",
        "activo": True,
        "anulado_at": None,
    }

    # Instancia ORM anulada lógicamente (RN-04)
    timestamp_anulacion = datetime(2026, 11, 1, 15, 30, 0, tzinfo=timezone.utc)
    categoria_anulada = Categoria(
        id=2,
        nombre="Bebidas Alcohólicas",
        descripcion=None,
        activo=False,
        anulado_at=timestamp_anulacion,
    )
    public_anulada = CategoriaPublic.model_validate(categoria_anulada)
    assert public_anulada.id == 2
    assert public_anulada.nombre == "Bebidas Alcohólicas"
    assert public_anulada.descripcion is None
    assert public_anulada.activo is False
    assert public_anulada.anulado_at == timestamp_anulacion


def test_categoria_public_no_es_modelo_de_tabla_y_no_se_registra_como_tabla() -> None:
    """Consigna: docs/consignas_examen_2.md, 4/R2 y 6.1 — los schemas de salida no exponen modelos de tabla."""
    # table=True no debe estar activo
    assert CategoriaPublic.model_config.get("table", False) is False
    assert not hasattr(CategoriaPublic, "__table__")

    # La tabla 'categorias' sí está registrada, pero CategoriaPublic no crea tabla
    assert "categorias" in SQLModel.metadata.tables
    assert "categoriapublic" not in SQLModel.metadata.tables
    assert getattr(CategoriaPublic, "__tablename__", "") not in SQLModel.metadata.tables
