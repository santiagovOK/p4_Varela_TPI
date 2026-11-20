"""Paquete de inicialización y carga de datos de base de datos para Food Store."""

from app.db.seed import run_seed, seed

__all__ = ["run_seed", "seed"]
