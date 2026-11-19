"""Pruebas unitarias de schemas SQLModel para Pedidos y DetallePedido (E2.2)."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.modules.pedidos import (
    CambioEstado,
    DetallePedido,
    DetallePedidoRead,
    ItemPedidoCreate,
    Pedido,
    PedidoCreate,
    PedidoRead,
    PedidosPaginados,
    ResumenPedidos,
)


def test_item_pedido_create_y_pedido_create_restricciones() -> None:
    """Valida RN-01 (items >= 1, cantidad >= 1) y RN-06 (forma_pago y direccion_entrega)."""
    item = ItemPedidoCreate(producto_id=1, cantidad=2)
    assert item.producto_id == 1
    assert item.cantidad == 2

    with pytest.raises(ValidationError):
        ItemPedidoCreate(producto_id=0, cantidad=1)

    with pytest.raises(ValidationError):
        ItemPedidoCreate(producto_id=1, cantidad=0)

    pedido = PedidoCreate(
        items=[item],
        forma_pago="TRANSFERENCIA",
        direccion_entrega="Av. Corrientes 1234",
    )
    assert pedido.notas is None
    assert pedido.forma_pago == "TRANSFERENCIA"

    # items vacío -> error (RN-01).
    with pytest.raises(ValidationError):
        PedidoCreate(
            items=[],
            forma_pago="EFECTIVO",
            direccion_entrega="Av. Corrientes 1234",
        )

    # forma_pago fuera de EFECTIVO / TRANSFERENCIA -> error (RN-06).
    with pytest.raises(ValidationError):
        PedidoCreate(
            items=[item],
            forma_pago="TARJETA",  # type: ignore[arg-type]
            direccion_entrega="Av. Corrientes 1234",
        )

    # direccion_entrega < 5 o > 200 -> error (RN-06).
    with pytest.raises(ValidationError):
        PedidoCreate(
            items=[item],
            forma_pago="EFECTIVO",
            direccion_entrega="1234",
        )

    with pytest.raises(ValidationError):
        PedidoCreate(
            items=[item],
            forma_pago="EFECTIVO",
            direccion_entrega="X" * 201,
        )


def test_pedido_read_paginados_cambio_estado_y_resumen() -> None:
    """Valida DTOs de salida, máquina de estados (RN-02) y ResumenPedidos."""
    now = datetime.now(timezone.utc)
    detalle = DetallePedido(
        id=1,
        pedido_id=10,
        producto_id=3,
        cantidad=2,
        nombre_producto="Pizza Muzzarella",
        precio_unitario=8500.0,
        subtotal=17000.0,
    )
    pedido = Pedido(
        id=10,
        usuario_id=5,
        estado="PENDIENTE",
        forma_pago="EFECTIVO",
        direccion_entrega="San Martín 500",
        notas="Tocar timbre",
        total=17000.0,
        created_at=now,
        updated_at=now,
        items=[detalle],
    )

    det_dto = DetallePedidoRead.model_validate(detalle)
    assert det_dto.nombre_producto == "Pizza Muzzarella"
    assert det_dto.subtotal == 17000.0

    ped_dto = PedidoRead.model_validate(pedido)
    assert ped_dto.id == 10
    assert ped_dto.estado == "PENDIENTE"
    assert len(ped_dto.items) == 1

    paginados = PedidosPaginados(total=1, items=[ped_dto])
    assert paginados.total == 1
    assert paginados.items[0].id == 10

    for estado in ("PENDIENTE", "EN_PREPARACION", "ENTREGADO", "CANCELADO"):
        cambio = CambioEstado(estado=estado)  # type: ignore[arg-type]
        assert cambio.estado == estado

    with pytest.raises(ValidationError):
        CambioEstado(estado="ANULADO")  # type: ignore[arg-type]

    resumen = ResumenPedidos(
        pendientes=2,
        en_preparacion=1,
        entregados=5,
        cancelados=1,
        pedidos_hoy=3,
        ingresos_entregados=45000.0,
    )
    assert resumen.ingresos_entregados == 45000.0
