"""Repositorio de acceso a datos para el módulo de Pedidos.

Consigna TPI (docs/consignas_tpi.md):
- Arquitectura en capas: Routers -> Services -> Unit of Work -> Repositories -> Models.
- Regla del Unit of Work: los repositorios solo usan ``add``, ``flush``, ``refresh`` y
  ``delete`` sobre la sesión compartida; nunca invocan ``session.commit()``.
- Módulos de dominio (PedidoRepository): implementa consultas por usuario
  (``list_by_usuario``), listados paginados, carga de ítems (``selectinload``) y
  agregaciones por estado (``count_by_estado``).
- API REST Pedidos y Schemas ResumenPedidos: soporta conteos por estado, pedidos
  del día e ingresos de pedidos ``ENTREGADO`` sin incluir reglas de negocio
  (``RN-01``..``RN-05`` viven en la capa Service).
- Criterio 3: Unit of Work y Repository.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.core.base_repository import BaseRepository
from app.modules.pedidos.models import DetallePedido, Pedido

ESTADOS_PEDIDO: tuple[str, ...] = (
    "PENDIENTE",
    "EN_PREPARACION",
    "ENTREGADO",
    "CANCELADO",
)


class PedidoRepository(BaseRepository[Pedido]):
    """Repositorio especializado para las entidades ``Pedido`` y ``DetallePedido``."""

    def __init__(self, session: Session) -> None:
        """Inicializa el repositorio de pedidos con la sesión compartida."""
        super().__init__(session, Pedido)

    def get_by_id(self, entity_id: Any) -> Pedido | None:
        """Obtiene un pedido por su ``id`` cargando anticipadamente sus ``items``."""
        statement = (
            select(Pedido)
            .where(Pedido.id == entity_id)
            .options(selectinload(Pedido.items))  # type: ignore[arg-type]
        )
        return self.session.exec(statement).first()

    def get_by_id_with_items(self, pedido_id: int) -> Pedido | None:
        """Alias explícito para obtener un pedido por ``id`` con ``items`` precargados."""
        return self.get_by_id(pedido_id)

    def add_detalle(self, detalle: DetallePedido) -> DetallePedido:
        """Agrega una línea ``DetallePedido`` a la sesión y sincroniza con ``flush``.

        Nunca ejecuta ``session.commit()``; la confirmación pertenece al UnitOfWork.
        """
        self.session.add(detalle)
        self.session.flush()
        self.session.refresh(detalle)
        return detalle

    def _list_filtered(
        self,
        conditions: list[Any],
        skip: int,
        limit: int,
    ) -> tuple[list[Pedido], int]:
        """Ejecuta consulta paginada y conteo total para una lista de condiciones."""
        count_stmt = select(func.count()).select_from(Pedido).where(*conditions)
        total = int(self.session.exec(count_stmt).one())

        items_stmt = (
            select(Pedido)
            .where(*conditions)
            .options(selectinload(Pedido.items))  # type: ignore[arg-type]
            .order_by(col(Pedido.created_at).desc(), col(Pedido.id).desc())
            .offset(skip)
            .limit(limit)
        )
        items = list(self.session.exec(items_stmt).all())
        return items, total

    def list_by_usuario(
        self,
        usuario_id: int,
        skip: int = 0,
        limit: int = 20,
        *,
        estado: str | None = None,
    ) -> tuple[list[Pedido], int]:
        """Lista los pedidos de un usuario con filtro opcional por ``estado`` y paginación."""
        conditions: list[Any] = [Pedido.usuario_id == usuario_id]
        if estado is not None:
            conditions.append(Pedido.estado == estado)
        return self._list_filtered(conditions, skip=skip, limit=limit)

    def list_all(
        self,
        estado: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Pedido], int]:
        """Lista todos los pedidos con filtro opcional por ``estado`` y paginación."""
        conditions: list[Any] = []
        if estado is not None:
            conditions.append(Pedido.estado == estado)
        return self._list_filtered(conditions, skip=skip, limit=limit)

    def list_paginado(
        self,
        estado: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Pedido], int]:
        """Alias de ``list_all`` para listados administrativos paginados."""
        return self.list_all(estado=estado, skip=skip, limit=limit)

    def count_by_estado(self) -> dict[str, int]:
        """Cuenta pedidos agrupados por estado garantizando las 4 claves del dominio."""
        conteos = {estado: 0 for estado in ESTADOS_PEDIDO}
        statement = select(Pedido.estado, func.count()).group_by(Pedido.estado)
        for estado, cantidad in self.session.exec(statement).all():
            if estado in conteos:
                conteos[estado] = int(cantidad)
        return conteos

    def count_estado(self, estado: str) -> int:
        """Cuenta la cantidad de pedidos en un estado específico."""
        statement = select(func.count()).select_from(Pedido).where(Pedido.estado == estado)
        return int(self.session.exec(statement).one())

    def count_pedidos_hoy(self, fecha_hoy: date | None = None) -> int:
        """Cuenta los pedidos creados en la fecha UTC indicada (por defecto hoy)."""
        fecha_objetivo = fecha_hoy or datetime.now(timezone.utc).date()
        inicio_dia = datetime.combine(fecha_objetivo, time.min, tzinfo=timezone.utc)
        fin_dia = inicio_dia + timedelta(days=1)
        statement = (
            select(func.count())
            .select_from(Pedido)
            .where(Pedido.created_at >= inicio_dia, Pedido.created_at < fin_dia)
        )
        return int(self.session.exec(statement).one())

    def sum_ingresos_entregados(self) -> float:
        """Suma el campo ``total`` de los pedidos en estado ``ENTREGADO``."""
        statement = (
            select(func.coalesce(func.sum(Pedido.total), 0.0))
            .select_from(Pedido)
            .where(Pedido.estado == "ENTREGADO")
        )
        return float(self.session.exec(statement).one())


__all__ = ["ESTADOS_PEDIDO", "PedidoRepository"]
