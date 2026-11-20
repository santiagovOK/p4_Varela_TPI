"""Servicio de lógica de negocio y excepciones para el módulo de Usuarios.

Consigna TPI (docs/consignas_tpi.md):
- Listado completo de usuarios para administración (incluyendo cuentas desactivadas)
  retornando ``UserPublic`` de 7 campos validado dentro del bloque ``with self.uow as uow:``.
- Activación y desactivación idempotentes (``disabled=False`` / ``disabled=True``).
- Error ``UsuarioNoEncontrado`` (``404``) si el usuario no existe.
- Error ``AutoDesactivacionNoPermitida`` (``400``) si el administrador intenta
  desactivarse a sí mismo (``current_user.id == id``).
- Sin llamadas a ``session.commit()`` en Service ni Router.
"""

from app.modules.usuarios.schemas import UserPublic
from app.modules.usuarios.unit_of_work import UsuarioUnitOfWork


class UsuarioNoEncontrado(LookupError):
    """Excepción de dominio cuando el usuario objetivo no existe en base de datos."""


class AutoDesactivacionNoPermitida(ValueError):
    """Excepción de dominio cuando un administrador intenta desactivar su propia cuenta."""


UsuarioNoEncontradoError = UsuarioNoEncontrado
AutoDesactivacionError = AutoDesactivacionNoPermitida


class UsuarioService:
    """Lógica de negocio para gestión administrativa de usuarios."""

    def __init__(self, uow: UsuarioUnitOfWork | None = None) -> None:
        self.uow = uow or UsuarioUnitOfWork()

    def list_usuarios(self) -> list[UserPublic]:
        """Lista todos los usuarios (activos y desactivados) ordenados por ``id``."""
        with self.uow as uow:
            usuarios = uow.usuarios.list_all()
            return [UserPublic.model_validate(usuario) for usuario in usuarios]

    listar_usuarios = list_usuarios

    def activar_usuario(self, usuario_id: int) -> UserPublic:
        """Activa una cuenta de usuario de forma idempotente (``disabled=False``)."""
        with self.uow as uow:
            usuario = uow.usuarios.get_by_id(usuario_id)
            if usuario is None:
                raise UsuarioNoEncontrado(f"Usuario con id {usuario_id} no encontrado")

            usuario.disabled = False
            actualizado = uow.usuarios.update(usuario)
            return UserPublic.model_validate(actualizado)

    activate_user = activar_usuario

    def desactivar_usuario(
        self,
        usuario_id: int,
        *,
        current_user_id: int | None = None,
    ) -> UserPublic:
        """Desactiva una cuenta de usuario de forma idempotente impidiendo auto-desactivación."""
        with self.uow as uow:
            if current_user_id is not None and usuario_id == current_user_id:
                raise AutoDesactivacionNoPermitida(
                    "No se permite desactivar la propia cuenta de administrador"
                )

            usuario = uow.usuarios.get_by_id(usuario_id)
            if usuario is None:
                raise UsuarioNoEncontrado(f"Usuario con id {usuario_id} no encontrado")

            usuario.disabled = True
            actualizado = uow.usuarios.update(usuario)
            return UserPublic.model_validate(actualizado)

    deactivate_user = desactivar_usuario


__all__ = [
    "AutoDesactivacionError",
    "AutoDesactivacionNoPermitida",
    "UsuarioNoEncontrado",
    "UsuarioNoEncontradoError",
    "UsuarioService",
]
