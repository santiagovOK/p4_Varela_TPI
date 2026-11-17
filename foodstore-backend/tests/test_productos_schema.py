"""Pruebas unitarias para schemas Pydantic y validaciones declarativas de Producto (E3.1).

Consigna: docs/consignas_examen_2.md, 3.1, 3.4/RN-01 a RN-11, 4/R2, 4/R3 y 6.1 — DTOs desacoplados de tablas persistentes.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.modules.categorias.schema import CategoriaPublic
from app.modules.productos.schema import (
    ProductoBase,
    ProductoCreate,
    ProductoPublic,
    ProductoUpdate,
)
from app.modules.unidades_medida.model import TipoUnidad, UnidadMedidaPublic


# ==============================================================================
# 1. Pruebas de ProductoCreate y ProductoUpdate válidos
# ==============================================================================


@pytest.mark.parametrize("dto_cls", [ProductoCreate, ProductoUpdate])
def test_producto_create_y_update_validos_preservan_precision_decimal(
    dto_cls: type[ProductoCreate | ProductoUpdate],
) -> None:
    """Verifica que Create y Update acepten datos válidos y preserven la precisión de Decimal en precio y stock."""
    payload: dict[str, Any] = {
        "nombre": "Harina 000",
        "descripcion": "Harina de trigo enriquecida ley 25630",
        "precio_base": Decimal("1050.50"),
        "unidad_venta_id": 1,
        "stock_cantidad": Decimal("250.75"),
        "disponible": True,
    }

    dto = dto_cls.model_validate(payload)

    assert dto.nombre == "Harina 000"
    assert dto.descripcion == "Harina de trigo enriquecida ley 25630"
    assert dto.precio_base == Decimal("1050.50")
    assert isinstance(dto.precio_base, Decimal)
    assert dto.unidad_venta_id == 1
    assert dto.stock_cantidad == Decimal("250.75")
    assert isinstance(dto.stock_cantidad, Decimal)
    assert dto.disponible is True


@pytest.mark.parametrize("dto_cls", [ProductoCreate, ProductoUpdate])
def test_producto_stock_omitido_resuelve_a_cero_y_descripcion_default_none(
    dto_cls: type[ProductoCreate | ProductoUpdate],
) -> None:
    """Verifica que stock_cantidad omitido resuelva a Decimal('0') y descripcion sea opcional con default None."""
    payload: dict[str, Any] = {
        "nombre": "Leche Entera",
        "precio_base": Decimal("850.00"),
        "unidad_venta_id": 2,
        "disponible": False,
    }

    dto = dto_cls.model_validate(payload)

    assert dto.nombre == "Leche Entera"
    assert dto.descripcion is None
    assert dto.stock_cantidad == Decimal("0")
    assert isinstance(dto.stock_cantidad, Decimal)
    assert dto.disponible is False


@pytest.mark.parametrize("dto_cls", [ProductoCreate, ProductoUpdate])
@pytest.mark.parametrize("stock_fraccionario", [Decimal("0.125"), "0.125"])
def test_producto_stock_fraccionario_aceptado_en_schema(
    dto_cls: type[ProductoCreate | ProductoUpdate],
    stock_fraccionario: Decimal | str,
) -> None:
    """Consigna: docs/consignas_examen_2.md, RN-10 — stock fraccionario no negativo es válido en schema.

    Nota: La validación de coherencia con unidad_medida contable pertenece al servicio E3.2, no al schema.
    """
    payload: dict[str, Any] = {
        "nombre": "Queso Parmesano al peso",
        "precio_base": Decimal("4500.00"),
        "unidad_venta_id": 1,
        "stock_cantidad": stock_fraccionario,
        "disponible": True,
    }

    dto = dto_cls.model_validate(payload)

    assert dto.stock_cantidad == Decimal("0.125")
    assert isinstance(dto.stock_cantidad, Decimal)


# ==============================================================================
# 2. Validaciones declarativas y rechazos en ProductoCreate y ProductoUpdate
# ==============================================================================


@pytest.mark.parametrize("dto_cls", [ProductoCreate, ProductoUpdate])
@pytest.mark.parametrize("nombre_invalido", ["", "a", "ab"])
def test_producto_nombre_menor_a_tres_caracteres_rechazado(
    dto_cls: type[ProductoCreate | ProductoUpdate],
    nombre_invalido: str,
) -> None:
    """Consigna: docs/consignas_examen_2.md, 3.4/RN-01 — nombre < 3 caracteres debe ser rechazado."""
    payload: dict[str, Any] = {
        "nombre": nombre_invalido,
        "precio_base": Decimal("100.00"),
        "unidad_venta_id": 1,
        "disponible": True,
    }

    with pytest.raises(ValidationError) as exc_info:
        dto_cls.model_validate(payload)

    errores = exc_info.value.errors()
    assert any(err["loc"] == ("nombre",) for err in errores)


@pytest.mark.parametrize("dto_cls", [ProductoCreate, ProductoUpdate])
def test_producto_nombre_tres_caracteres_limite_aceptado(
    dto_cls: type[ProductoCreate | ProductoUpdate],
) -> None:
    """Verifica que el límite exacto de 3 caracteres en nombre sea aceptado."""
    payload: dict[str, Any] = {
        "nombre": "Pan",
        "precio_base": Decimal("50.00"),
        "unidad_venta_id": 1,
        "disponible": True,
    }

    dto = dto_cls.model_validate(payload)
    assert dto.nombre == "Pan"


@pytest.mark.parametrize("dto_cls", [ProductoCreate, ProductoUpdate])
def test_producto_precio_base_negativo_rechazado_y_cero_aceptado(
    dto_cls: type[ProductoCreate | ProductoUpdate],
) -> None:
    """Verifica que precio_base < 0 sea rechazado y precio_base == 0 sea aceptado."""
    payload_invalido: dict[str, Any] = {
        "nombre": "Aceite de Oliva",
        "precio_base": Decimal("-0.01"),
        "unidad_venta_id": 1,
        "disponible": True,
    }

    with pytest.raises(ValidationError) as exc_info:
        dto_cls.model_validate(payload_invalido)

    errores = exc_info.value.errors()
    assert any(err["loc"] == ("precio_base",) for err in errores)

    payload_cero: dict[str, Any] = {
        "nombre": "Muestra Gratis",
        "precio_base": Decimal("0"),
        "unidad_venta_id": 1,
        "disponible": True,
    }
    dto_cero = dto_cls.model_validate(payload_cero)
    assert dto_cero.precio_base == Decimal("0")


@pytest.mark.parametrize("dto_cls", [ProductoCreate, ProductoUpdate])
def test_producto_stock_cantidad_negativo_rechazado_y_cero_aceptado(
    dto_cls: type[ProductoCreate | ProductoUpdate],
) -> None:
    """Verifica que stock_cantidad < 0 sea rechazado y stock_cantidad == 0 sea aceptado."""
    payload_invalido: dict[str, Any] = {
        "nombre": "Fideos Tallarines",
        "precio_base": Decimal("300.00"),
        "unidad_venta_id": 1,
        "stock_cantidad": Decimal("-1"),
        "disponible": True,
    }

    with pytest.raises(ValidationError) as exc_info:
        dto_cls.model_validate(payload_invalido)

    errores = exc_info.value.errors()
    assert any(err["loc"] == ("stock_cantidad",) for err in errores)

    payload_cero: dict[str, Any] = {
        "nombre": "Fideos Tallarines",
        "precio_base": Decimal("300.00"),
        "unidad_venta_id": 1,
        "stock_cantidad": Decimal("0"),
        "disponible": True,
    }
    dto_cero = dto_cls.model_validate(payload_cero)
    assert dto_cero.stock_cantidad == Decimal("0")


@pytest.mark.parametrize("dto_cls", [ProductoCreate, ProductoUpdate])
@pytest.mark.parametrize("unidad_id_invalida", [0, -1, -100])
def test_producto_unidad_venta_id_menor_a_uno_rechazado(
    dto_cls: type[ProductoCreate | ProductoUpdate],
    unidad_id_invalida: int,
) -> None:
    """Verifica que unidad_venta_id < 1 sea rechazado con ValidationError."""
    payload: dict[str, Any] = {
        "nombre": "Arroz Blanco",
        "precio_base": Decimal("400.00"),
        "unidad_venta_id": unidad_id_invalida,
        "disponible": True,
    }

    with pytest.raises(ValidationError) as exc_info:
        dto_cls.model_validate(payload)

    errores = exc_info.value.errors()
    assert any(err["loc"] == ("unidad_venta_id",) for err in errores)


@pytest.mark.parametrize("dto_cls", [ProductoCreate, ProductoUpdate])
@pytest.mark.parametrize(
    "campo_faltante",
    ["nombre", "precio_base", "unidad_venta_id", "disponible"],
)
def test_producto_campos_obligatorios_omitidos_lanzan_validation_error(
    dto_cls: type[ProductoCreate | ProductoUpdate],
    campo_faltante: str,
) -> None:
    """Consigna: docs/consignas_examen_2.md, 4/R3 — PUT/POST completo requiere todos los campos normativos."""
    base_payload: dict[str, Any] = {
        "nombre": "Tomates Perita",
        "precio_base": Decimal("600.00"),
        "unidad_venta_id": 1,
        "disponible": True,
    }
    del base_payload[campo_faltante]

    with pytest.raises(ValidationError) as exc_info:
        dto_cls.model_validate(base_payload)

    errores = exc_info.value.errors()
    assert any(err["loc"] == (campo_faltante,) for err in errores)


@pytest.mark.parametrize("dto_cls", [ProductoCreate, ProductoUpdate])
@pytest.mark.parametrize(
    "campo_nulo",
    ["nombre", "precio_base", "unidad_venta_id", "disponible"],
)
def test_producto_campos_obligatorios_nulos_lanzan_validation_error(
    dto_cls: type[ProductoCreate | ProductoUpdate],
    campo_nulo: str,
) -> None:
    """Verifica que pasar None a campos obligatorios lance ValidationError."""
    base_payload: dict[str, Any] = {
        "nombre": "Tomates Perita",
        "precio_base": Decimal("600.00"),
        "unidad_venta_id": 1,
        "disponible": True,
    }
    base_payload[campo_nulo] = None

    with pytest.raises(ValidationError) as exc_info:
        dto_cls.model_validate(base_payload)

    errores = exc_info.value.errors()
    assert any(err["loc"] == (campo_nulo,) for err in errores)


def test_producto_update_payload_parcial_rechazado() -> None:
    """Consigna: docs/consignas_examen_2.md, 4/R3 — PUT es completo, no PATCH; solo nombre no es válido."""
    payload_parcial: dict[str, Any] = {
        "nombre": "Nuevo Nombre",
    }

    with pytest.raises(ValidationError) as exc_info:
        ProductoUpdate.model_validate(payload_parcial)

    locs = [err["loc"][0] for err in exc_info.value.errors()]
    assert "precio_base" in locs
    assert "unidad_venta_id" in locs
    assert "disponible" in locs


# ==============================================================================
# 3. Pruebas de ProductoPublic y anidamiento relacional
# ==============================================================================


def test_producto_public_con_relaciones_anidadas_valido() -> None:
    """Consigna: docs/consignas_examen_2.md, 4/R3 y 6.1 — response_model ProductoPublic con unidad y categorias."""
    unidad = UnidadMedidaPublic(
        id=1,
        nombre="Kilogramo",
        simbolo="kg",
        tipo=TipoUnidad.peso,
    )
    categoria = CategoriaPublic(
        id=10,
        nombre="Almacén",
        descripcion="Productos secos y no perecederos",
        activo=True,
        anulado_at=None,
    )

    data: dict[str, Any] = {
        "id": 42,
        "nombre": "Yerba Mate 1kg",
        "descripcion": "Yerba mate con palo",
        "precio_base": Decimal("1800.00"),
        "unidad_venta_id": 1,
        "stock_cantidad": Decimal("15.0"),
        "disponible": True,
        "activo": True,
        "anulado_at": None,
        "unidad_venta": unidad,
        "categorias": [categoria],
        "hay_stock": True,
    }

    dto = ProductoPublic.model_validate(data)

    assert dto.id == 42
    assert dto.nombre == "Yerba Mate 1kg"
    assert dto.precio_base == Decimal("1800.00")
    assert dto.activo is True
    assert dto.anulado_at is None
    assert dto.unidad_venta.id == 1
    assert dto.unidad_venta.simbolo == "kg"
    assert len(dto.categorias) == 1
    assert dto.categorias[0].id == 10
    assert dto.categorias[0].nombre == "Almacén"
    assert dto.hay_stock is True


def test_producto_public_acepta_lista_de_categorias_vacia() -> None:
    """Verifica que un producto sin categorías asociadas acepte categorias=[] en ProductoPublic."""
    data: dict[str, Any] = {
        "id": 99,
        "nombre": "Agua Mineral 2L",
        "descripcion": None,
        "precio_base": Decimal("500.00"),
        "unidad_venta_id": 2,
        "stock_cantidad": Decimal("0"),
        "disponible": False,
        "activo": True,
        "anulado_at": None,
        "unidad_venta": {
            "id": 2,
            "nombre": "Litro",
            "simbolo": "l",
            "tipo": "volumen",
        },
        "categorias": [],
        "hay_stock": False,
    }

    dto = ProductoPublic.model_validate(data)

    assert dto.id == 99
    assert dto.categorias == []
    assert dto.hay_stock is False
    assert dto.disponible is False
    assert dto.stock_cantidad == Decimal("0")


def test_producto_public_con_anulado_at_timestamp() -> None:
    """Verifica que un producto anulado admita datetime válido en anulado_at y activo=False."""
    ahora = datetime.now(timezone.utc)
    data: dict[str, Any] = {
        "id": 5,
        "nombre": "Galletitas Descontinuadas",
        "descripcion": "Fuera de línea",
        "precio_base": Decimal("350.00"),
        "unidad_venta_id": 1,
        "stock_cantidad": Decimal("0"),
        "disponible": False,
        "activo": False,
        "anulado_at": ahora,
        "unidad_venta": {
            "id": 1,
            "nombre": "Kilogramo",
            "simbolo": "kg",
            "tipo": "peso",
        },
        "categorias": [],
        "hay_stock": False,
    }

    dto = ProductoPublic.model_validate(data)

    assert dto.activo is False
    assert dto.anulado_at == ahora


def test_producto_public_hay_stock_requerido_omision_lanza_validation_error() -> None:
    """Consigna: docs/consignas_examen_2.md, 4/R3 — hay_stock es requerido en el contrato público (calculado en servicio)."""
    data: dict[str, Any] = {
        "id": 1,
        "nombre": "Azúcar Ledesma",
        "precio_base": Decimal("800.00"),
        "unidad_venta_id": 1,
        "stock_cantidad": Decimal("10"),
        "disponible": True,
        "activo": True,
        "anulado_at": None,
        "unidad_venta": {
            "id": 1,
            "nombre": "Kilogramo",
            "simbolo": "kg",
            "tipo": "peso",
        },
        "categorias": [],
        # "hay_stock" omitido intencionalmente
    }

    with pytest.raises(ValidationError) as exc_info:
        ProductoPublic.model_validate(data)

    errores = exc_info.value.errors()
    assert any(err["loc"] == ("hay_stock",) for err in errores)


def test_producto_public_unidad_venta_invalida_lanza_validation_error_anidado() -> None:
    """Verifica que datos inválidos en el objeto anidado unidad_venta disparen ValidationError con loc='unidad_venta'."""
    data: dict[str, Any] = {
        "id": 1,
        "nombre": "Café Tostado",
        "precio_base": Decimal("3000.00"),
        "unidad_venta_id": 1,
        "stock_cantidad": Decimal("5"),
        "disponible": True,
        "activo": True,
        "anulado_at": None,
        "unidad_venta": {
            "id": 1,
            "nombre": "Kilogramo",
            # "simbolo" omitido intencionalmente
            "tipo": "peso",
        },
        "categorias": [],
        "hay_stock": True,
    }

    with pytest.raises(ValidationError) as exc_info:
        ProductoPublic.model_validate(data)

    errores = exc_info.value.errors()
    # Verifica que el error se anide en ('unidad_venta', 'simbolo')
    assert any(
        err["loc"][0] == "unidad_venta" and "simbolo" in err["loc"]
        for err in errores
    )


def test_producto_public_categoria_anidada_invalida_lanza_validation_error() -> None:
    """Verifica que una categoría anidada sin nombre lance ValidationError con loc hacia categorias."""
    data: dict[str, Any] = {
        "id": 1,
        "nombre": "Té en Saquitos",
        "precio_base": Decimal("1200.00"),
        "unidad_venta_id": 1,
        "stock_cantidad": Decimal("20"),
        "disponible": True,
        "activo": True,
        "anulado_at": None,
        "unidad_venta": {
            "id": 1,
            "nombre": "Kilogramo",
            "simbolo": "kg",
            "tipo": "peso",
        },
        "categorias": [
            {
                "id": 1,
                # "nombre" omitido intencionalmente
                "activo": True,
            }
        ],
        "hay_stock": True,
    }

    with pytest.raises(ValidationError) as exc_info:
        ProductoPublic.model_validate(data)

    errores = exc_info.value.errors()
    # Verifica que el error se anide en ('categorias', 0, 'nombre')
    assert any(err["loc"][0] == "categorias" for err in errores)
