"""Repositorio genérico base sobre SQLModel para acceso a datos sin commits.

Consigna TPI (docs/consignas_tpi.md):
- Arquitectura en capas: Routers -> Services -> Unit of Work -> Repositories -> Models.
- Unit of Work y Repository: BaseRepository[T] concentra operaciones CRUD comunes.
- Regla del Unit of Work: los repositorios solo usan add, flush, refresh y delete;
  nunca llaman a session.commit(), delegando la transacción al UnitOfWork.
- Componentes del núcleo (app/core/base_repository.py): implementación genérica
  BaseRepository[T] con get_by_id, get_all, add y delete.
- Criterio 3: Unit of Work y Repository.
"""

from typing import Any, Generic, TypeVar

from sqlmodel import Session, SQLModel, select

T = TypeVar("T", bound=SQLModel)
ModelType = T


class BaseRepository(Generic[T]):
    """Repositorio genérico base para entidades SQLModel.

    Encapsula las operaciones de persistencia sobre una ``Session`` compartida
    sin confirmar transacciones (sin ``commit``), siguiendo el patrón
    Repository + Unit of Work definido en ``docs/consignas_tpi.md``.
    """

    def __init__(self, session: Session, model: type[T]) -> None:
        """Inicializa el repositorio con una sesión activa y el modelo objetivo."""
        self.session = session
        self.model = model

    def get_by_id(self, entity_id: Any) -> T | None:
        """Obtiene una entidad por su clave primaria o ``None`` si no existe."""
        return self.session.get(self.model, entity_id)

    def get_all(
        self,
        skip: int = 0,
        limit: int | None = None,
        *,
        offset: int | None = None,
    ) -> list[T]:
        """Lista entidades con paginación opcional mediante ``skip``/``offset`` y ``limit``."""
        effective_offset = offset if offset is not None else skip
        statement = select(self.model).offset(effective_offset)
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.session.exec(statement).all())

    def add(self, entity: T) -> T:
        """Agrega o actualiza una entidad en la sesión y sincroniza cambios con ``flush``.

        Nunca ejecuta ``session.commit()``; la confirmación pertenece al UnitOfWork.
        """
        self.session.add(entity)
        self.session.flush()
        self.session.refresh(entity)
        return entity

    def delete(self, entity: T) -> None:
        """Elimina una entidad de la sesión y sincroniza con ``flush`` sin confirmar."""
        self.session.delete(entity)
        self.session.flush()

    def create(self, entity: T) -> T:
        """Alias semántico de ``add`` para creación de entidades."""
        return self.add(entity)

    def update(self, entity: T) -> T:
        """Alias semántico de ``add`` para actualización de entidades."""
        return self.add(entity)


__all__ = ["BaseRepository", "ModelType", "T"]
