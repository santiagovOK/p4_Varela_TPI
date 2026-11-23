"""Servicio de lógica de negocio para el módulo de Categorías.

Consigna TPI (docs/consignas_tpi.pdf):
- Arquitectura en capas: Routers -> Services -> Unit of Work -> Repositories -> Models.
- Regla del Unit of Work: el servicio coordina transacciones mediante
  ``with self.uow as uow:``, nunca invoca ``session.commit()`` y valida los DTOs
  (``CategoriaRead.model_validate(...)``) dentro del bloque ``with``.
- API REST Categorías: lecturas públicas de categorías activas, normalización
  ``.strip()`` en ``nombre``, ``NombreDuplicado`` (409) aun sobre bajas lógicas,
  ``CategoriaNoEncontrada`` (404) y baja lógica (``activo=False``).
"""

from app.modules.categorias.models import Categoria
from app.modules.categorias.schemas import CategoriaCreate, CategoriaRead, CategoriaUpdate
from app.modules.categorias.unit_of_work import CategoriaUnitOfWork


class CategoriaNoEncontrada(LookupError):
    """Se lanza cuando la categoría no existe o fue dada de baja lógica."""


class NombreDuplicado(ValueError):
    """Se lanza cuando ya existe una categoría (activa o inactiva) con el mismo nombre."""


class DatosCategoriaInvalidos(ValueError):
    """Se lanza cuando los datos normalizados de la categoría incumplen las reglas."""


CategoriaNoEncontradaError = CategoriaNoEncontrada
NombreDuplicadoError = NombreDuplicado


def _normalizar_nombre(nombre: str) -> str:
    """Recorta espacios externos y valida longitud significativa de 2 a 100 caracteres."""
    nombre_limpio = nombre.strip()
    if len(nombre_limpio) < 2 or len(nombre_limpio) > 100:
        raise DatosCategoriaInvalidos(
            "El nombre de la categoría debe tener entre 2 y 100 caracteres significativos."
        )
    return nombre_limpio


def _normalizar_descripcion(descripcion: str | None) -> str | None:
    """Recorta espacios externos de la descripción cuando no es nula."""
    if descripcion is None:
        return None
    return descripcion.strip()


class CategoriaService:
    """Servicio de casos de uso para el catálogo de categorías."""

    def __init__(self, uow: CategoriaUnitOfWork | None = None) -> None:
        """Inicializa el servicio con un Unit of Work de categorías."""
        self.uow = uow or CategoriaUnitOfWork()

    def list_categorias(self) -> list[CategoriaRead]:
        """Lista todas las categorías activas ordenadas por ``id``."""
        with self.uow as uow:
            categorias = uow.categorias.list_activas()
            return [CategoriaRead.model_validate(categoria) for categoria in categorias]

    def get_categoria(self, categoria_id: int) -> CategoriaRead:
        """Obtiene una categoría activa por su ``id`` o lanza ``CategoriaNoEncontrada``."""
        with self.uow as uow:
            categoria = uow.categorias.get_activa_by_id(categoria_id)
            if categoria is None:
                raise CategoriaNoEncontrada(
                    f"Categoría con id {categoria_id} no encontrada."
                )
            return CategoriaRead.model_validate(categoria)

    def create_categoria(self, data: CategoriaCreate) -> CategoriaRead:
        """Crea una categoría nueva validando unicidad incluso frente a inactivas."""
        nombre_limpio = _normalizar_nombre(data.nombre)
        descripcion_limpia = _normalizar_descripcion(data.descripcion)

        with self.uow as uow:
            if uow.categorias.get_by_nombre(nombre_limpio) is not None:
                raise NombreDuplicado(
                    f"Ya existe una categoría con el nombre '{nombre_limpio}'."
                )

            nueva = Categoria(
                nombre=nombre_limpio,
                descripcion=descripcion_limpia,
                activo=True,
            )
            creada = uow.categorias.add(nueva)
            return CategoriaRead.model_validate(creada)

    def update_categoria(self, categoria_id: int, data: CategoriaUpdate) -> CategoriaRead:
        """Actualiza parcialmente una categoría activa usando ``exclude_unset=True``."""
        campos = data.model_dump(exclude_unset=True)

        with self.uow as uow:
            categoria = uow.categorias.get_activa_by_id(categoria_id)
            if categoria is None:
                raise CategoriaNoEncontrada(
                    f"Categoría con id {categoria_id} no encontrada."
                )

            if "nombre" in campos:
                nombre_raw = campos["nombre"]
                if nombre_raw is None:
                    raise DatosCategoriaInvalidos(
                        "El nombre de la categoría no puede ser nulo."
                    )
                nombre_limpio = _normalizar_nombre(nombre_raw)
                existente = uow.categorias.get_by_nombre(nombre_limpio)
                if existente is not None and existente.id != categoria.id:
                    raise NombreDuplicado(
                        f"Ya existe una categoría con el nombre '{nombre_limpio}'."
                    )
                categoria.nombre = nombre_limpio

            if "descripcion" in campos:
                categoria.descripcion = _normalizar_descripcion(campos["descripcion"])

            actualizada = uow.categorias.update(categoria)
            return CategoriaRead.model_validate(actualizada)

    def delete_categoria(self, categoria_id: int) -> None:
        """Realiza la baja lógica (``activo=False``) de una categoría activa."""
        with self.uow as uow:
            categoria = uow.categorias.get_activa_by_id(categoria_id)
            if categoria is None:
                raise CategoriaNoEncontrada(
                    f"Categoría con id {categoria_id} no encontrada."
                )
            categoria.activo = False
            uow.categorias.update(categoria)

    listar_categorias = list_categorias
    obtener_categoria = get_categoria
    crear_categoria = create_categoria
    actualizar_categoria = update_categoria
    eliminar_categoria = delete_categoria


__all__ = [
    "CategoriaNoEncontrada",
    "CategoriaNoEncontradaError",
    "CategoriaService",
    "DatosCategoriaInvalidos",
    "NombreDuplicado",
    "NombreDuplicadoError",
]
