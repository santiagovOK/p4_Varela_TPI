"""Servicio de lógica de negocio para el módulo de Productos (base lista para migración TPI)."""

from fastapi import HTTPException, status

__all__: list[str] = []


def not_implemented_error() -> HTTPException:
    """Retorna error 501 mientras se completa la migración al contrato TPI."""
    return HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Módulo de productos pendiente de migración al contrato TPI.",
    )
