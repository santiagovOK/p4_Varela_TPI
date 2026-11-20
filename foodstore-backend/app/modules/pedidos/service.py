"""Servicio de lógica de negocio para el módulo de Pedidos.

Consigna TPI (docs/consignas_tpi.md):
- Arquitectura en capas: Routers -> Services -> Unit of Work -> Repositories -> Models.
- Regla del Unit of Work: el servicio coordina transacciones mediante
  ``with self.uow as uow:``, nunca invoca ``session.commit()`` y construye
  ``PedidoRead.model_validate(...)`` dentro del bloque ``with`` con las líneas
  cargadas explícitamente vía ``uow.pedidos.get_by_id_with_items(...)``.
- RN-01: Creación transaccional desde el carrito con validación de productos
  activos/disponibles, stock suficiente, no repetición, descuento de stock y
  snapshot inmutable de nombre/precio en una sola transacción atómica.
- RN-02: Máquina de 4 estados (``PENDIENTE``, ``EN_PREPARACION``, ``ENTREGADO``,
  ``CANCELADO``) con estados terminales inmutables.
- RN-03: Restitución atómica e idempotente de stock al cancelar pedidos.
- RN-05: Inmutabilidad de líneas y total tras la creación.
- RN-06: Validación de forma de pago y longitud normalizada de ``direccion_entrega``.
"""

from datetime import datetime, timezone

from app.modules.pedidos.models import DetallePedido, Pedido
from app.modules.pedidos.schemas import (
    CambioEstado,
    EstadoPedido,
    PedidoCreate,
    PedidoRead,
    PedidosPaginados,
    ResumenPedidos,
)
from app.modules.pedidos.unit_of_work import PedidoUnitOfWork
from app.modules.productos.service import ProductoNoEncontrado

TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    "PENDIENTE": {"EN_PREPARACION", "CANCELADO"},
    "EN_PREPARACION": {"ENTREGADO", "CANCELADO"},
    "ENTREGADO": set(),
    "CANCELADO": set(),
}


class PedidoNoEncontrado(LookupError):
    """Se lanza cuando el pedido solicitado no existe en la base de datos."""


class PedidoAjeno(PermissionError):
    """Se lanza cuando un usuario intenta acceder o cancelar un pedido de otro titular (RN-04)."""


class TransicionInvalida(ValueError):
    """Se lanza cuando la transición de estado solicitada incumple RN-02."""


class ProductoRepetido(ValueError):
    """Se lanza cuando el pedido contiene líneas con el mismo ``producto_id``."""


class ProductoNoDisponible(ValueError):
    """Se lanza cuando un producto activo no está disponible para la venta."""


class StockInsuficiente(ValueError):
    """Se lanza cuando el stock actual es menor que la cantidad solicitada."""


class DatosPedidoInvalidos(ValueError):
    """Se lanza cuando los datos normalizados del pedido incumplen las reglas."""


def _normalizar_direccion_entrega(direccion: str) -> str:
    """Recorta espacios externos y valida que la dirección tenga entre 5 y 200 caracteres."""
    direccion_limpia = direccion.strip()
    if not (5 <= len(direccion_limpia) <= 200):
        raise DatosPedidoInvalidos(
            "La dirección de entrega debe tener entre 5 y 200 caracteres."
        )
    return direccion_limpia


def _normalizar_notas(notas: str | None) -> str | None:
    """Recorta espacios externos de notas opcionales, devolviendo ``None`` si quedan vacías."""
    if notas is None:
        return None
    notas_limpias = notas.strip()
    return notas_limpias or None


def _restituir_stock(uow: PedidoUnitOfWork, pedido: Pedido) -> None:
    """Restituye el stock de cada línea del pedido dentro de la transacción activa (RN-03)."""
    for item in pedido.items:
        producto = uow.productos.get_by_id(item.producto_id)
        if producto is not None:
            producto.stock += item.cantidad
            uow.productos.update(producto)


class PedidoService:
    """Servicio de casos de uso para la gestión transaccional de pedidos."""

    TRANSICIONES_VALIDAS = TRANSICIONES_VALIDAS

    def __init__(self, uow: PedidoUnitOfWork | None = None) -> None:
        """Inicializa el servicio con un Unit of Work de pedidos."""
        self.uow = uow or PedidoUnitOfWork()

    def create_pedido(self, usuario_id: int, data: PedidoCreate) -> PedidoRead:
        """Crea un pedido transaccional desde el carrito aplicando RN-01, RN-05 y RN-06."""
        direccion_limpia = _normalizar_direccion_entrega(data.direccion_entrega)
        notas_limpias = _normalizar_notas(data.notas)

        if not data.items:
            raise DatosPedidoInvalidos("El pedido debe incluir al menos un ítem.")

        vistos: set[int] = set()
        for item in data.items:
            if item.producto_id in vistos:
                raise ProductoRepetido(
                    f"El producto con id {item.producto_id} está repetido en el pedido."
                )
            vistos.add(item.producto_id)

        with self.uow as uow:
            pedido = uow.pedidos.add(
                Pedido(
                    usuario_id=usuario_id,
                    estado="PENDIENTE",
                    forma_pago=data.forma_pago,
                    direccion_entrega=direccion_limpia,
                    notas=notas_limpias,
                    total=0.0,
                )
            )
            assert pedido.id is not None

            total = 0.0
            for item in data.items:
                producto = uow.productos.get_activo_by_id(item.producto_id)
                if producto is None:
                    raise ProductoNoEncontrado(
                        f"Producto con id {item.producto_id} no encontrado."
                    )
                if not producto.disponible:
                    raise ProductoNoDisponible(
                        f"El producto '{producto.nombre}' no está disponible."
                    )
                if producto.stock < item.cantidad:
                    raise StockInsuficiente(
                        f"Stock insuficiente para '{producto.nombre}': "
                        f"disponible {producto.stock}, solicitado {item.cantidad}."
                    )

                producto.stock -= item.cantidad
                uow.productos.update(producto)

                assert producto.id is not None
                precio_unitario = float(producto.precio_base)
                subtotal = round(precio_unitario * item.cantidad, 2)
                uow.pedidos.add_detalle(
                    DetallePedido(
                        pedido_id=pedido.id,
                        producto_id=producto.id,
                        cantidad=item.cantidad,
                        nombre_producto=producto.nombre,
                        precio_unitario=precio_unitario,
                        subtotal=subtotal,
                    )
                )
                total += subtotal

            pedido.total = round(total, 2)
            uow.pedidos.update(pedido)

            hidratado = uow.pedidos.get_by_id_with_items(pedido.id)
            assert hidratado is not None
            return PedidoRead.model_validate(hidratado)

    crear_pedido = create_pedido

    def cambiar_estado(
        self,
        pedido_id: int,
        data: CambioEstado | EstadoPedido | str,
    ) -> PedidoRead:
        """Cambia el estado de un pedido aplicando RN-02 y restitución de stock RN-03."""
        nuevo_estado = data.estado if isinstance(data, CambioEstado) else str(data)

        with self.uow as uow:
            pedido = uow.pedidos.get_by_id_with_items(pedido_id)
            if pedido is None:
                raise PedidoNoEncontrado(
                    f"Pedido con id {pedido_id} no encontrado."
                )

            permitidos = self.TRANSICIONES_VALIDAS.get(pedido.estado, set())
            if nuevo_estado not in permitidos:
                raise TransicionInvalida(
                    f"Transición de estado inválida: '{pedido.estado}' -> '{nuevo_estado}'."
                )

            if nuevo_estado == "CANCELADO":
                _restituir_stock(uow, pedido)

            pedido.estado = nuevo_estado
            pedido.updated_at = datetime.now(timezone.utc)
            uow.pedidos.update(pedido)

            assert pedido.id is not None
            hidratado = uow.pedidos.get_by_id_with_items(pedido.id)
            assert hidratado is not None
            return PedidoRead.model_validate(hidratado)

    update_estado = cambiar_estado
    avanzar_estado = cambiar_estado

    def list_pedidos(
        self,
        *,
        usuario_id: int,
        role: str,
        skip: int = 0,
        limit: int = 20,
        estado: EstadoPedido | str | None = None,
    ) -> PedidosPaginados:
        """Lista todos los pedidos para ``admin`` o solo los propios para ``user`` (RN-04)."""
        with self.uow as uow:
            if role == "admin":
                items, total = uow.pedidos.list_all(
                    estado=estado,
                    skip=skip,
                    limit=limit,
                )
            else:
                items, total = uow.pedidos.list_by_usuario(
                    usuario_id=usuario_id,
                    skip=skip,
                    limit=limit,
                    estado=estado,
                )
            items_dto = [PedidoRead.model_validate(pedido) for pedido in items]
            return PedidosPaginados(total=total, items=items_dto)

    listar_pedidos = list_pedidos

    def get_pedido(
        self,
        pedido_id: int,
        *,
        usuario_id: int,
        role: str,
    ) -> PedidoRead:
        """Obtiene el detalle de un pedido validando existencia y propiedad/rol (RN-04)."""
        with self.uow as uow:
            pedido = uow.pedidos.get_by_id_with_items(pedido_id)
            if pedido is None:
                raise PedidoNoEncontrado(
                    f"Pedido con id {pedido_id} no encontrado."
                )
            if role != "admin" and pedido.usuario_id != usuario_id:
                raise PedidoAjeno(
                    "No tiene permisos para consultar un pedido de otro usuario."
                )
            return PedidoRead.model_validate(pedido)

    obtener_pedido = get_pedido

    def cancelar_pedido(
        self,
        pedido_id: int,
        *,
        usuario_id: int,
    ) -> PedidoRead:
        """Cancela un pedido propio en estado ``PENDIENTE`` restituyendo stock (RN-03, RN-04)."""
        with self.uow as uow:
            pedido = uow.pedidos.get_by_id_with_items(pedido_id)
            if pedido is None:
                raise PedidoNoEncontrado(
                    f"Pedido con id {pedido_id} no encontrado."
                )
            if pedido.usuario_id != usuario_id:
                raise PedidoAjeno(
                    "Solo el dueño del pedido puede cancelarlo por esta vía."
                )
            if pedido.estado != "PENDIENTE":
                raise TransicionInvalida(
                    f"Solo se puede cancelar un pedido en estado 'PENDIENTE' (actual: '{pedido.estado}')."
                )

            _restituir_stock(uow, pedido)

            pedido.estado = "CANCELADO"
            pedido.updated_at = datetime.now(timezone.utc)
            uow.pedidos.update(pedido)

            assert pedido.id is not None
            hidratado = uow.pedidos.get_by_id_with_items(pedido.id)
            assert hidratado is not None
            return PedidoRead.model_validate(hidratado)

    def get_resumen(self) -> ResumenPedidos:
        """Calcula los indicadores administrativos de pedidos para el panel (E6.4)."""
        with self.uow as uow:
            conteos = uow.pedidos.count_by_estado()
            pedidos_hoy = uow.pedidos.count_pedidos_hoy()
            ingresos_entregados = round(uow.pedidos.sum_ingresos_entregados(), 2)
            return ResumenPedidos(
                pendientes=conteos.get("PENDIENTE", 0),
                en_preparacion=conteos.get("EN_PREPARACION", 0),
                entregados=conteos.get("ENTREGADO", 0),
                cancelados=conteos.get("CANCELADO", 0),
                pedidos_hoy=pedidos_hoy,
                ingresos_entregados=ingresos_entregados,
            )

    obtener_resumen = get_resumen


__all__ = [
    "TRANSICIONES_VALIDAS",
    "DatosPedidoInvalidos",
    "PedidoAjeno",
    "PedidoNoEncontrado",
    "PedidoService",
    "ProductoNoDisponible",
    "ProductoNoEncontrado",
    "ProductoRepetido",
    "StockInsuficiente",
    "TransicionInvalida",
]
