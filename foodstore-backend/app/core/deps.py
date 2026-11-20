"""Dependencias transversales de autenticación por cookie HttpOnly y autorización por rol."""

from collections.abc import Callable, Sequence
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import ACCESS_TOKEN_TYPE, decode_access_token
from app.modules.usuarios.models import Usuario

ACCESS_COOKIE_NAME = "access_token"


def _unauthorized_exception() -> HTTPException:
    """Construye la excepción estándar 401 para credenciales o cookie ausente/inválida."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )


class OAuth2PasswordBearerWithCookie(OAuth2):
    """Esquema OAuth2 que extrae el JWT exclusivamente desde la cookie HttpOnly `access_token`."""

    def __init__(
        self,
        tokenUrl: str,
        cookie_name: str = ACCESS_COOKIE_NAME,
        scheme_name: str | None = None,
        scopes: dict[str, str] | None = None,
        description: str | None = None,
        auto_error: bool = True,
    ) -> None:
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes or {}})
        super().__init__(
            flows=flows,
            scheme_name=scheme_name,
            description=description,
            auto_error=auto_error,
        )
        self.cookie_name = cookie_name

    async def __call__(self, request: Request) -> str | None:
        """Lee únicamente la cookie configurada e ignora la cabecera `Authorization`."""
        raw_token = request.cookies.get(self.cookie_name)
        if not isinstance(raw_token, str) or not raw_token.strip():
            if self.auto_error:
                raise _unauthorized_exception()
            return None
        return raw_token.strip()


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/api/v1/auth/token")


def get_token_from_cookie(request: Request) -> str:
    """Extrae el JWT exclusivamente desde la cookie `access_token` de la petición."""
    raw_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not isinstance(raw_token, str) or not raw_token.strip():
        raise _unauthorized_exception()
    return raw_token.strip()


def get_current_user(
    request: Request,
    session: Session = Depends(get_session),
    token: str | None = Depends(oauth2_scheme),
) -> Usuario:
    """Valida el JWT de la cookie `access_token` y consulta autoritativamente la BD."""
    raw_token = token.strip() if isinstance(token, str) and token.strip() else get_token_from_cookie(request)

    payload = decode_access_token(raw_token)
    if payload is None:
        raise _unauthorized_exception()

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise _unauthorized_exception()

    username = payload.get("sub")
    role = payload.get("role")
    if not isinstance(username, str) or not username.strip():
        raise _unauthorized_exception()
    if not isinstance(role, str) or not role.strip():
        raise _unauthorized_exception()

    user = session.exec(select(Usuario).where(Usuario.username == username.strip())).first()
    if user is None:
        raise _unauthorized_exception()

    return user


def get_current_active_user(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Usuario:
    """Verifica que el usuario autenticado no tenga la cuenta desactivada."""
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuenta de usuario desactivada",
        )
    return current_user


def require_role(allowed_roles: Sequence[str] | set[str] | str) -> Callable[..., Usuario]:
    """Fábrica de dependencias que exige que el usuario activo posea un rol permitido."""
    if isinstance(allowed_roles, str):
        normalized_roles = {allowed_roles.strip()} if allowed_roles.strip() else set()
    else:
        normalized_roles = {
            role.strip()
            for role in allowed_roles
            if isinstance(role, str) and role.strip()
        }

    if not normalized_roles:
        raise ValueError("allowed_roles debe contener al menos un rol válido.")

    def role_checker(
        current_user: Annotated[Usuario, Depends(get_current_active_user)],
    ) -> Usuario:
        if current_user.role not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos suficientes para realizar esta acción",
            )
        return current_user

    return role_checker


CurrentUserDep = Annotated[Usuario, Depends(get_current_user)]
CurrentActiveUserDep = Annotated[Usuario, Depends(get_current_active_user)]
AdminUserDep = Annotated[Usuario, Depends(require_role(["admin"]))]

__all__ = [
    "ACCESS_COOKIE_NAME",
    "AdminUserDep",
    "CurrentActiveUserDep",
    "CurrentUserDep",
    "OAuth2PasswordBearerWithCookie",
    "get_current_active_user",
    "get_current_user",
    "get_token_from_cookie",
    "oauth2_scheme",
    "require_role",
]
