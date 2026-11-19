"""Repositorio de acceso a datos para el módulo de Categorías.

Consigna TPI (docs/consignas_tpi.md):
- Arquitectura en capas: Routers -> Services -> Unit of Work -> Repositories -> Models.
- Regla del Unit of Work: los repositorios encapsulan consultas y persistencia sobre
  una ``Session`` compartida (``add``, ``flush``, ``refresh``, ``delete``) sin invocar
  nunca ``session.commit()``.
- Módulos de dominio (categorias): ``CategoriaRepository`` extiende ``BaseRepository[Categoria]``
  con ``get_by_nombre`` y consultas sobre categorías activas.
- API REST Categorías: el borrado lógico (``activo=False``) no libera el ``nombre`` único
  en base de datos, por lo que ``get_by_nombre`` consulta todas las categorías.
- Criterio 3: Unit of Work y Repository.
"""

from sqlmodel import Session, col, select

from app.core.base_repository import BaseRepository
from app.modules.categorias.models import Categoria


class CategoriaRepository(BaseRepository[Categoria]):
    """Repositorio especializado para la entidad ``Categoria``."""

    def __init__(self, session: Session) -> None:
        """Inicializa el repositorio de categorías con la sesión compartida."""
        super().__init__(session, Categoria)

    def get_by_nombre(self, nombre: str) -> Categoria | None:
        """Busca una categoría por nombre exacto incluyendo inactivas.

        La baja lógica (``activo=False``) conserva la restricción ``unique`` sobre
        ``categorias.nombre`` (docs/consignas_tpi.md: API REST Categorías).
        """
        statement = select(Categoria).where(Categoria.nombre == nombre)
        return self.session.exec(statement).first()

    def list_activas(
        self,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[Categoria]:
        """Lista las categorías activas ordenadas por ``id`` con paginación opcional."""
        statement = (
            select(Categoria)
            .where(col(Categoria.activo).is_(True))
            .order_by(col(Categoria.id))
            .offset(skip)
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.session.exec(statement).all())

    def get_all_activas(
        self,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[Categoria]:
        """Alias de ``list_activas`` para listar categorías activas paginadas."""
        return self.list_activas(skip=skip, limit=limit)

    def get_activa_by_id(self, categoria_id: int) -> Categoria | None:
        """Obtiene una categoría activa por su ``id`` o ``None`` si no existe o está inactiva."""
        statement = select(Categoria).where(
            Categoria.id == categoria_id,
            col(Categoria.activo).is_(True),
        )
        return self.session.exec(statement).first()


__all__ = ["CategoriaRepository"]
