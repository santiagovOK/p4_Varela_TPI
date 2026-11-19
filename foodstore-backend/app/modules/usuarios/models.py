"""Modelo de dominio SQLModel para Usuarios.

Consigna TPI (docs/consignas_tpi.md):
- Modelo de dominio Usuario: tabla `usuarios` con `id`, `username` (único),
  `full_name`, `email` (único), `hashed_password`, `role`, `disabled` y
  `created_at`.
- Modelos y relaciones 1:N: relación `Usuario.pedidos` (`back_populates="usuario"`).
- Criterio 2: Modelo de datos.
- Criterio 4: Autenticación y usuarios.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.pedidos.models import Pedido


class Usuario(SQLModel, table=True):
    """Entidad de dominio para usuarios del sistema."""

    __tablename__ = "usuarios"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(
        min_length=1,
        max_length=50,
        nullable=False,
        index=True,
        unique=True,
    )
    full_name: str = Field(min_length=1, max_length=150, nullable=False)
    email: str = Field(
        min_length=3,
        max_length=254,
        nullable=False,
        index=True,
        unique=True,
    )
    hashed_password: str = Field(min_length=1, max_length=255, nullable=False)
    role: str = Field(
        default="user",
        min_length=1,
        max_length=30,
        nullable=False,
    )
    disabled: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relación 1:N con Pedido (docs/consignas_tpi.md: Modelos y relaciones Usuario.pedidos).
    pedidos: list["Pedido"] = Relationship(back_populates="usuario")


__all__ = ["Usuario"]
