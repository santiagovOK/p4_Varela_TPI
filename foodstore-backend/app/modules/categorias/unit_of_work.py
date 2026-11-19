"""Unit of Work para el módulo de Categorías.

Consigna TPI (docs/consignas_tpi.md):
- Arquitectura en capas: Routers -> Services -> Unit of Work -> Repositories -> Models.
- Regla del Unit of Work: ``CategoriaUnitOfWork`` hereda de ``UnitOfWork`` (sesión
  con ``expire_on_commit=False``, commit/rollback y close automático en ``__exit__``)
  e instancia sus repositorios sobre la sesión activa en ``_init_repositories``.
- Criterio 3: Unit of Work y Repository.
"""

from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.categorias.repository import CategoriaRepository


class CategoriaUnitOfWork(UnitOfWork):
    """Coordinador transaccional para operaciones sobre categorías."""

    categorias: CategoriaRepository

    def _init_repositories(self, session: Session) -> None:
        """Inicializa ``CategoriaRepository`` compartiendo la sesión del UoW."""
        self.categorias = CategoriaRepository(session)


__all__ = ["CategoriaUnitOfWork"]
