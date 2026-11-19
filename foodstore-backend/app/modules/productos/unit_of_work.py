"""Unit of Work para el módulo de Productos.

Consigna TPI (docs/consignas_tpi.md):
- Arquitectura en capas: Routers -> Services -> Unit of Work -> Repositories -> Models.
- Regla del Unit of Work: ``ProductoUnitOfWork`` administra una única ``Session``
  con ``expire_on_commit=False`` compartida entre ``ProductoRepository`` y
  ``CategoriaRepository`` para validar la categoría y persistir productos en una
  misma transacción atómica.
- Schemas ``model_validate``: habilita la construcción de ``ProductoRead`` con
  ``categoria`` anidada dentro del bloque ``with``.
- Criterio 3: Unit of Work y Repository.
"""

from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.categorias.repository import CategoriaRepository
from app.modules.productos.repository import ProductoRepository


class ProductoUnitOfWork(UnitOfWork):
    """Coordinador transaccional para operaciones sobre productos y sus categorías."""

    productos: ProductoRepository
    categorias: CategoriaRepository

    def _init_repositories(self, session: Session) -> None:
        """Instancia ``productos`` y ``categorias`` compartiendo la misma sesión."""
        self.productos = ProductoRepository(session)
        self.categorias = CategoriaRepository(session)


__all__ = ["ProductoUnitOfWork"]
