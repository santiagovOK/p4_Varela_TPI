"""Repositorio de acceso a datos para el módulo de Usuarios.

Consigna TPI (docs/consignas_tpi.md):
- Arquitectura en capas: Routers -> Services -> Unit of Work -> Repositories -> Models.
- Regla del Unit of Work: los repositorios solo usan add, flush, refresh y delete;
  nunca llaman a session.commit(), delegando la transacción al UnitOfWork.
- Módulos de dominio (usuarios): ``UsuarioRepository`` extiende ``BaseRepository[Usuario]``
  e implementa ``get_by_username`` y ``get_by_email``.
- API REST Usuarios: ``GET /admin/usuarios`` retorna todas las cuentas (activas y
  desactivadas) en orden determinístico ascendente por ``id``.
"""

from sqlmodel import Session, col, select

from app.core.base_repository import BaseRepository
from app.modules.usuarios.models import Usuario


class UsuarioRepository(BaseRepository[Usuario]):
    """Repositorio especializado para la entidad ``Usuario``."""

    def __init__(self, session: Session) -> None:
        """Inicializa el repositorio de usuarios con la sesión compartida."""
        super().__init__(session, Usuario)

    def get_by_username(self, username: str) -> Usuario | None:
        """Busca un usuario por ``username`` exacto (activo o desactivado)."""
        statement = select(Usuario).where(Usuario.username == username.strip())
        return self.session.exec(statement).first()

    def get_by_email(self, email: str) -> Usuario | None:
        """Busca un usuario por ``email`` exacto (activo o desactivado)."""
        statement = select(Usuario).where(Usuario.email == email.strip())
        return self.session.exec(statement).first()

    def list_all(
        self,
        skip: int = 0,
        limit: int | None = None,
        *,
        offset: int | None = None,
    ) -> list[Usuario]:
        """Lista todos los usuarios (activos y desactivados) ordenados por ``id`` ascendente."""
        effective_offset = offset if offset is not None else skip
        statement = (
            select(Usuario)
            .order_by(col(Usuario.id))
            .offset(effective_offset)
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.session.exec(statement).all())

    def get_all(
        self,
        skip: int = 0,
        limit: int | None = None,
        *,
        offset: int | None = None,
    ) -> list[Usuario]:
        """Sobrescribe ``BaseRepository.get_all`` garantizando orden determinístico por ``id``."""
        return self.list_all(skip=skip, limit=limit, offset=offset)


__all__ = ["UsuarioRepository"]
