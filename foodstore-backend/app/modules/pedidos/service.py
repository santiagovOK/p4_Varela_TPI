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
- RN-05: Inmutabilidad de líneas y total tras la creación.
- RN-06: Validación de forma de pago y longitud normalizada de ``direccion_entrega``.
"""

from app.modules.pedidos.models import DetallePedido, Pedido
from app.modules.pedidos.schemas import PedidoCreate, PedidoRead
from app.modules.pedidos.unit_of_work import PedidoUnitOfWork
from app.modules.productos.service import ProductoNoEncontrado


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


class PedidoService:
    """Servicio de casos de uso para la gestión transaccional de pedidos."""

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


__all__ = [
    "DatosPedidoInvalidos",
    "PedidoService",
    "ProductoNoDisponible",
    "ProductoNoEncontrado",
    "ProductoRepetido",
    "StockInsuficiente",
]
