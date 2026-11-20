"""Servicio de dominio y excepciones para el módulo de Autenticación.

Consigna TPI (docs/consignas_tpi.md):
- Registro público (role="user", disabled=False, bcrypt) con rechazo 409 (UsuarioDuplicado).
- Autenticación contra BD (401 si credenciales inválidas, 400 si cuenta desactivada).
- Consulta autoritativa en BD por username para validar sesión activa.
- Unit of Work con expire_on_commit=False y conversión a UserPublic dentro del bloque `with`.
- Criterio 4: Autenticación y usuarios.
"""

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app.core.security import hash_password, verify_password
from app.core.unit_of_work import UnitOfWork
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import UserCreate, UserPublic


class UsuarioDuplicado(ValueError):
    """Excepción de dominio cuando el username o email ya está registrado."""


class CredencialesInvalidas(ValueError):
    """Excepción de dominio cuando las credenciales o sesión son inválidas."""


class CuentaDesactivada(ValueError):
    """Excepción de dominio cuando la cuenta de usuario está desactivada."""


UsuarioDuplicadoError = UsuarioDuplicado
CredencialesInvalidasError = CredencialesInvalidas
UsuarioDesactivadoError = CuentaDesactivada
AuthUnitOfWork = UnitOfWork


class AuthService:
    """Lógica de negocio de registro, autenticación y consulta de sesión."""

    def __init__(self, uow: UnitOfWork | None = None) -> None:
        self.uow = uow or UnitOfWork()

    def register(self, data: UserCreate) -> UserPublic:
        """Registra un nuevo usuario con rol fijo 'user' y contraseña hasheada con bcrypt."""
        username = data.username.strip()
        full_name = data.full_name.strip()
        email = str(data.email).strip()

        if not username:
            raise CredencialesInvalidas("El nombre de usuario no puede estar vacío.")
        if not full_name:
            raise CredencialesInvalidas("El nombre completo no puede estar vacío.")

        try:
            with self.uow as uow:
                assert uow.session is not None
                existing_user = uow.session.exec(
                    select(Usuario).where(
                        (Usuario.username == username) | (Usuario.email == email)
                    )
                ).first()
                if existing_user is not None:
                    raise UsuarioDuplicado("El nombre de usuario o el email ya están registrados.")

                user = Usuario(
                    username=username,
                    full_name=full_name,
                    email=email,
                    hashed_password=hash_password(data.password),
                    role="user",
                    disabled=False,
                )
                uow.session.add(user)
                uow.session.flush()
                uow.session.refresh(user)
                return UserPublic.model_validate(user)
        except IntegrityError as exc:
            raise UsuarioDuplicado("El nombre de usuario o el email ya están registrados.") from exc

    crear = register

    def authenticate(self, username: str, password: str) -> UserPublic:
        """Verifica credenciales en BD y que la cuenta no esté desactivada."""
        normalized_username = username.strip()
        if not normalized_username or not password:
            raise CredencialesInvalidas("Usuario o contraseña incorrectos")

        with self.uow as uow:
            assert uow.session is not None
            user = uow.session.exec(
                select(Usuario).where(Usuario.username == normalized_username)
            ).first()
            if user is None or not verify_password(password, user.hashed_password):
                raise CredencialesInvalidas("Usuario o contraseña incorrectos")
            if user.disabled:
                raise CuentaDesactivada("Cuenta de usuario desactivada")
            return UserPublic.model_validate(user)

    autenticar = authenticate

    def get_active_user_by_username(self, username: str) -> UserPublic:
        """Obtiene el usuario autoritativo desde BD y valida que esté activo."""
        normalized_username = username.strip()
        if not normalized_username:
            raise CredencialesInvalidas("No autenticado")

        with self.uow as uow:
            assert uow.session is not None
            user = uow.session.exec(
                select(Usuario).where(Usuario.username == normalized_username)
            ).first()
            if user is None:
                raise CredencialesInvalidas("No autenticado")
            if user.disabled:
                raise CuentaDesactivada("Cuenta de usuario desactivada")
            return UserPublic.model_validate(user)


__all__ = [
    "AuthService",
    "AuthUnitOfWork",
    "CredencialesInvalidas",
    "CredencialesInvalidasError",
    "CuentaDesactivada",
    "UsuarioDesactivadoError",
    "UsuarioDuplicado",
    "UsuarioDuplicadoError",
]
