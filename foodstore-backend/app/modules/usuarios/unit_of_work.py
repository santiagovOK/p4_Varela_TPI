"""Unit of Work para el módulo de Usuarios.

Consigna TPI (docs/consignas_tpi.md):
- Arquitectura en capas: Routers -> Services -> Unit of Work -> Repositories -> Models.
- Regla del Unit of Work: ``UsuarioUnitOfWork`` hereda de ``UnitOfWork`` (sesión
  con ``expire_on_commit=False``, commit/rollback y close automático en ``__exit__``)
  e instancia sus repositorios sobre la sesión activa en ``_init_repositories``.
- Criterio 3: Unit of Work y Repository.
- Criterio 4: Autenticación y usuarios.
"""

from sqlmodel import Session

from app.core.unit_of_work import UnitOfWork
from app.modules.usuarios.repository import UsuarioRepository


class UsuarioUnitOfWork(UnitOfWork):
    """Coordinador transaccional para operaciones administrativas sobre usuarios."""

    usuarios: UsuarioRepository

    def _init_repositories(self, session: Session) -> None:
        """Inicializa ``UsuarioRepository`` compartiendo la sesión del UoW."""
        self.usuarios = UsuarioRepository(session)


__all__ = ["UsuarioUnitOfWork"]
