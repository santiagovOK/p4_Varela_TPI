"""Abstracción base de Unit of Work para coordinación transaccional.

Consigna TPI (docs/consignas_tpi.pdf):
- Unit of Work y Repository: gestión centralizada de transacciones mediante
  context manager (``with self.uow as uow:``).
- Regla del Unit of Work: la sesión se abre con ``expire_on_commit=False`` en
  ``__enter__`` y se confirma (``commit``) o revierte (``rollback``) en
  ``__exit__``, garantizando el cierre (``close``) en ``finally``.
- Schemas ``model_validate`` con ``expire_on_commit=False``: permite construir
  DTOs con relaciones dentro del bloque ``with`` y acceder a atributos tras el
  commit sin ``DetachedInstanceError``.
- Componentes del núcleo (app/core/unit_of_work.py): clase ``UnitOfWork``.
- Criterio 3: Unit of Work y Repository.
"""

from collections.abc import Callable
from types import TracebackType
from typing import Self

from sqlmodel import Session

from app.core.database import session_factory as default_session_factory


class UnitOfWork:
    """Gestor transaccional base que administra el ciclo de vida de una ``Session``.

    Las subclases de cada módulo sobrescriben ``_init_repositories`` para
    instanciar sus repositorios compartiendo la misma sesión de trabajo.
    """

    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        """Inicializa el Unit of Work con una fábrica de sesiones configurable."""
        self.session_factory = session_factory or default_session_factory
        self.session: Session | None = None

    def _init_repositories(self, session: Session) -> None:
        """Hook para que las subclases inicialicen repositorios sobre ``session``."""

    def __enter__(self) -> Self:
        """Abre la sesión con ``expire_on_commit=False`` e inicializa repositorios."""
        self.session = self.session_factory()
        # Regla Unit of Work: evita expiración de atributos tras commit (model_validate).
        if hasattr(self.session, "expire_on_commit"):
            self.session.expire_on_commit = False
        try:
            self._init_repositories(self.session)
        except BaseException:
            self.session.close()
            self.session = None
            raise
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Confirma si no hubo errores o revierte ante excepción, cerrando siempre."""
        if self.session is None:
            return
        try:
            if exc_type is not None:
                self.session.rollback()
            else:
                try:
                    self.session.commit()
                except BaseException:
                    self.session.rollback()
                    raise
        finally:
            self.session.close()
            self.session = None

    def commit(self) -> None:
        """Confirma manualmente la transacción de la sesión activa."""
        if self.session is None:
            raise RuntimeError("No hay una sesión activa en UnitOfWork.")
        self.session.commit()

    def rollback(self) -> None:
        """Revierte manualmente la transacción de la sesión activa."""
        if self.session is None:
            raise RuntimeError("No hay una sesión activa en UnitOfWork.")
        self.session.rollback()


UnitOfWorkBase = UnitOfWork

__all__ = ["UnitOfWork", "UnitOfWorkBase"]
