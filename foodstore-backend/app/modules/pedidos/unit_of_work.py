"""Unit of Work para el módulo de Pedidos.

Consigna TPI (docs/consignas_tpi.pdf):
- Arquitectura en capas: Routers -> Services -> Unit of Work -> Repositories -> Models.
- Regla del Unit of Work: ``PedidoUnitOfWork`` administra una única ``Session``
  con ``expire_on_commit=False`` compartida entre ``PedidoRepository`` y
  ``ProductoRepository``.
- Flujo de crear pedido con Unit of Work: permite validar/descontar stock de
  productos, crear el pedido con sus líneas de detalle y confirmar todo en una
  misma transacción atómica (o revertir íntegramente ante cualquier error).
- Criterio 3: Unit of Work y Repository.
"""

from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.pedidos.repository import PedidoRepository
from app.modules.productos.repository import ProductoRepository


class PedidoUnitOfWork(UnitOfWork):
    """Coordinador transaccional para operaciones atómicas sobre pedidos y productos."""

    pedidos: PedidoRepository
    productos: ProductoRepository

    def _init_repositories(self, session: Session) -> None:
        """Instancia ``pedidos`` y ``productos`` compartiendo exactamente la misma sesión."""
        self.pedidos = PedidoRepository(session)
        self.productos = ProductoRepository(session)


__all__ = ["PedidoUnitOfWork"]
