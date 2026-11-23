"""Repositorio de acceso a datos para el módulo de Productos.

Consigna TPI (docs/consignas_tpi.pdf):
- Arquitectura en capas: Routers -> Services -> Unit of Work -> Repositories -> Models.
- Regla del Unit of Work: los repositorios solo usan ``add``, ``flush``, ``refresh`` y
  ``delete`` sobre la sesión compartida; nunca invocan ``session.commit()``.
- Módulos de dominio (productos): ``ProductoRepository`` extiende ``BaseRepository[Producto]``
  con ``search`` (filtros por ``search``/``nombre``, ``categoria_id``, ``disponible`` y
  paginación ``skip``/``limit``).
- API REST Productos y Schemas ``model_validate``: las lecturas cargan de forma anticipada
  la relación ``Producto.categoria`` (``selectinload``) para validar ``ProductoRead``
  dentro del bloque ``with self.uow as uow:``.
- Criterio 3: Unit of Work y Repository.
"""

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.core.base_repository import BaseRepository
from app.modules.productos.models import Producto


class ProductoRepository(BaseRepository[Producto]):
    """Repositorio especializado para la entidad ``Producto``."""

    def __init__(self, session: Session) -> None:
        """Inicializa el repositorio de productos con la sesión compartida."""
        super().__init__(session, Producto)

    def get_by_id(self, entity_id: Any, *, for_update: bool = False) -> Producto | None:
        """Obtiene un producto por su ``id`` cargando anticipadamente ``categoria``."""
        statement = (
            select(Producto)
            .where(Producto.id == entity_id)
            .options(selectinload(Producto.categoria))  # type: ignore[arg-type]
        )
        if for_update:
            statement = statement.with_for_update()
        return self.session.exec(statement).first()

    def get_activo_by_id(
        self, producto_id: int, *, for_update: bool = False
    ) -> Producto | None:
        """Obtiene un producto activo por su ``id`` cargando ``categoria``."""
        statement = (
            select(Producto)
            .where(
                Producto.id == producto_id,
                col(Producto.activo).is_(True),
            )
            .options(selectinload(Producto.categoria))  # type: ignore[arg-type]
        )
        if for_update:
            statement = statement.with_for_update()
        return self.session.exec(statement).first()

    def search(
        self,
        search: str | None = None,
        categoria_id: int | None = None,
        disponible: bool | None = None,
        skip: int = 0,
        limit: int = 20,
        *,
        nombre: str | None = None,
    ) -> tuple[list[Producto], int]:
        """Busca productos activos aplicando filtros y paginación.

        Devuelve ``(items, total)`` con ``Producto.categoria`` precargada mediante
        ``selectinload`` y orden determinístico por ``Producto.id``.
        """
        conditions: list[Any] = [col(Producto.activo).is_(True)]

        termino = search if search is not None else nombre
        if termino is not None and termino.strip():
            conditions.append(col(Producto.nombre).ilike(f"%{termino.strip()}%"))

        if categoria_id is not None:
            conditions.append(Producto.categoria_id == categoria_id)

        if disponible is not None:
            conditions.append(col(Producto.disponible).is_(disponible))

        count_stmt = select(func.count()).select_from(Producto).where(*conditions)
        total = int(self.session.exec(count_stmt).one())

        items_stmt = (
            select(Producto)
            .where(*conditions)
            .options(selectinload(Producto.categoria))  # type: ignore[arg-type]
            .order_by(col(Producto.id))
            .offset(skip)
            .limit(limit)
        )
        items = list(self.session.exec(items_stmt).all())
        return items, total


__all__ = ["ProductoRepository"]
