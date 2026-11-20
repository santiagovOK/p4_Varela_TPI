"""Router FastAPI para los endpoints de Autenticación (`/api/v1/auth/*`).

Consigna TPI (docs/consignas_tpi.md):
- POST /api/v1/auth/register -> 201 UserPublic (7 campos) / 409 UsuarioDuplicado.
- POST /api/v1/auth/token -> 200 {"message": "Login exitoso"} + cookie HttpOnly `access_token`.
- POST /api/v1/auth/logout -> 200 eliminando cookie `access_token`.
- GET /api/v1/auth/me -> 200 UserPublic consultando BD desde cookie `access_token`.
- Criterio 4: Autenticación y usuarios.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.security import create_access_token, decode_access_token
from app.core.unit_of_work import UnitOfWork
from app.modules.auth.schemas import LoginMessage, LogoutMessage, UserCreate, UserPublic
from app.modules.auth.service import (
    AuthService,
    CredencialesInvalidas,
    CuentaDesactivada,
    UsuarioDuplicado,
)

ACCESS_COOKIE_NAME = "access_token"
ACCESS_COOKIE = ACCESS_COOKIE_NAME

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def get_auth_service(session: Session = Depends(get_session)) -> AuthService:
    """Construye AuthService usando el bind transaccional de la sesión inyectada."""
    bind = session.get_bind()
    return AuthService(UnitOfWork(lambda: Session(bind, expire_on_commit=False)))


def _resolve_cookie_secure(current_settings: Settings) -> bool:
    """Resuelve el flag `secure` de la cookie desde Settings."""
    return current_settings.cookie_secure


def _resolve_current_active_user_from_cookie(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserPublic:
    """Extrae el JWT exclusivamente de la cookie `access_token` y consulta BD."""
    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if not isinstance(username, str) or not username.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return service.get_active_user_by_username(username)
    except CredencialesInvalidas as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except CuentaDesactivada as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuenta de usuario desactivada",
        ) from exc


try:
    from app.core.deps import get_current_active_user as _core_get_current_active_user
except ImportError:
    _core_get_current_active_user = None


def get_current_active_user_for_me(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserPublic:
    """Dependencia para `/me`: delega a app.core.deps si existe (E4.3) o usa cookie local."""
    if _core_get_current_active_user is not None:
        session_gen = get_session()
        session = next(session_gen)
        try:
            user = _core_get_current_active_user(request=request, session=session)
            return UserPublic.model_validate(user)
        finally:
            try:
                next(session_gen)
            except StopIteration:
                pass
    return _resolve_current_active_user_from_cookie(request=request, service=service)


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
)
def register(
    data: UserCreate,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserPublic:
    """Crea una cuenta pública con rol 'user' y contraseña hasheada con bcrypt."""
    try:
        return service.register(data)
    except UsuarioDuplicado as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except CredencialesInvalidas as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/token",
    response_model=LoginMessage,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión con cookie HttpOnly",
)
def login_for_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginMessage:
    """Autentica usuario y emite la cookie HttpOnly `access_token` sin exponer el JWT."""
    try:
        user = service.authenticate(form_data.username, form_data.password)
    except CredencialesInvalidas as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except CuentaDesactivada as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuenta de usuario desactivada",
        ) from exc

    current_settings = get_settings()
    token = create_access_token(
        {"sub": user.username, "role": user.role},
        role=user.role,
    )
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=_resolve_cookie_secure(current_settings),
        samesite="lax",
        path="/",
        max_age=current_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return LoginMessage(message="Login exitoso")


@router.post(
    "/logout",
    response_model=LogoutMessage,
    status_code=status.HTTP_200_OK,
    summary="Cerrar sesión",
)
def logout(response: Response) -> LogoutMessage:
    """Elimina la cookie HttpOnly `access_token`."""
    current_settings = get_settings()
    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=_resolve_cookie_secure(current_settings),
        samesite="lax",
    )
    return LogoutMessage(message="Sesión cerrada")


@router.get(
    "/me",
    response_model=UserPublic,
    status_code=status.HTTP_200_OK,
    summary="Obtener perfil del usuario autenticado",
)
def read_users_me(
    current_user: Annotated[UserPublic, Depends(get_current_active_user_for_me)],
) -> UserPublic:
    """Retorna el perfil del usuario autenticado validado contra la base de datos."""
    return UserPublic.model_validate(current_user)


__all__ = [
    "ACCESS_COOKIE",
    "ACCESS_COOKIE_NAME",
    "get_auth_service",
    "login_for_access_token",
    "logout",
    "read_users_me",
    "register",
    "router",
]
