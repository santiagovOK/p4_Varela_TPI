"""Servicio de lógica de negocio para el módulo de Productos.

Consigna TPI (docs/consignas_tpi.md):
- Arquitectura en capas: Routers -> Services -> Unit of Work -> Repositories -> Models.
- Regla del Unit of Work: el servicio coordina transacciones mediante
  ``with self.uow as uow:``, nunca invoca ``session.commit()`` y construye
  ``ProductoRead.model_validate(...)`` dentro del bloque ``with`` con la relación
  ``categoria`` cargada explícitamente vía ``uow.productos.get_activo_by_id(...)``.
- API REST Productos (E5.2): listado paginado ``{total, items}`` con filtros
  ``search``, ``categoria_id`` y ``disponible``, detalle activo, creación y
  actualización parcial (``exclude_unset=True``) validando categoría activa.
"""

from app.modules.categorias.service import CategoriaNoEncontrada
from app.modules.productos.models import Producto
from app.modules.productos.schemas import (
    ProductoCreate,
    ProductoRead,
    ProductoStockUpdate,
    ProductoUpdate,
    ProductosPaginados,
)
from app.modules.productos.unit_of_work import ProductoUnitOfWork


class ProductoNoEncontrado(LookupError):
    """Se lanza cuando el producto no existe o fue dado de baja lógica."""


class DatosProductoInvalidos(ValueError):
    """Se lanza cuando los datos normalizados del producto incumplen las reglas."""


ProductoNoEncontradoError = ProductoNoEncontrado


def _normalizar_nombre_producto(nombre: str) -> str:
    """Recorta espacios externos y verifica que el nombre no quede vacío."""
    nombre_limpio = nombre.strip()
    if not nombre_limpio:
        raise DatosProductoInvalidos(
            "El nombre del producto no puede estar vacío ni contener solo espacios."
        )
    return nombre_limpio


def _normalizar_texto_opcional(valor: str | None) -> str | None:
    """Recorta espacios externos de campos textuales opcionales."""
    if valor is None:
        return None
    return valor.strip()


class ProductoService:
    """Servicio de casos de uso para el catálogo de productos."""

    def __init__(self, uow: ProductoUnitOfWork | None = None) -> None:
        """Inicializa el servicio con un Unit of Work de productos."""
        self.uow = uow or ProductoUnitOfWork()

    def list_productos(
        self,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
        categoria_id: int | None = None,
        disponible: bool | None = None,
    ) -> ProductosPaginados:
        """Lista productos activos paginados y filtrados en formato ``{total, items}``."""
        with self.uow as uow:
            items, total = uow.productos.search(
                search=search,
                categoria_id=categoria_id,
                disponible=disponible,
                skip=skip,
                limit=limit,
            )
            return ProductosPaginados(
                total=total,
                items=[ProductoRead.model_validate(item) for item in items],
            )

    def get_producto(self, producto_id: int) -> ProductoRead:
        """Obtiene un producto activo por su ``id`` con su categoría cargada."""
        with self.uow as uow:
            producto = uow.productos.get_activo_by_id(producto_id)
            if producto is None:
                raise ProductoNoEncontrado(
                    f"Producto con id {producto_id} no encontrado."
                )
            return ProductoRead.model_validate(producto)

    def create_producto(self, data: ProductoCreate) -> ProductoRead:
        """Crea un producto validando que la categoría exista y esté activa."""
        nombre_limpio = _normalizar_nombre_producto(data.nombre)
        descripcion_limpia = _normalizar_texto_opcional(data.descripcion)
        imagen_limpia = _normalizar_texto_opcional(data.imagen_url)

        with self.uow as uow:
            categoria = uow.categorias.get_activa_by_id(data.categoria_id)
            if categoria is None:
                raise CategoriaNoEncontrada(
                    f"Categoría con id {data.categoria_id} no encontrada o inactiva."
                )

            nuevo = Producto(
                nombre=nombre_limpio,
                descripcion=descripcion_limpia,
                precio_base=data.precio_base,
                imagen_url=imagen_limpia,
                stock=data.stock,
                disponible=data.disponible,
                categoria_id=data.categoria_id,
                activo=True,
            )
            creado = uow.productos.add(nuevo)
            assert creado.id is not None
            hidratado = uow.productos.get_activo_by_id(creado.id)
            assert hidratado is not None
            return ProductoRead.model_validate(hidratado)

    def update_producto(self, producto_id: int, data: ProductoUpdate) -> ProductoRead:
        """Actualiza parcialmente un producto activo usando ``exclude_unset=True``."""
        campos = data.model_dump(exclude_unset=True)

        with self.uow as uow:
            producto = uow.productos.get_activo_by_id(producto_id)
            if producto is None:
                raise ProductoNoEncontrado(
                    f"Producto con id {producto_id} no encontrado."
                )

            if "categoria_id" in campos:
                categoria_id = campos["categoria_id"]
                if categoria_id is None:
                    raise DatosProductoInvalidos(
                        "La categoría del producto no puede ser nula."
                    )
                categoria = uow.categorias.get_activa_by_id(categoria_id)
                if categoria is None:
                    raise CategoriaNoEncontrada(
                        f"Categoría con id {categoria_id} no encontrada o inactiva."
                    )
                producto.categoria_id = categoria_id

            if "nombre" in campos:
                nombre_raw = campos["nombre"]
                if nombre_raw is None:
                    raise DatosProductoInvalidos(
                        "El nombre del producto no puede ser nulo."
                    )
                producto.nombre = _normalizar_nombre_producto(nombre_raw)

            if "descripcion" in campos:
                producto.descripcion = _normalizar_texto_opcional(campos["descripcion"])

            if "imagen_url" in campos:
                producto.imagen_url = _normalizar_texto_opcional(campos["imagen_url"])

            for campo in ("precio_base", "stock", "disponible"):
                if campo in campos:
                    valor = campos[campo]
                    if valor is None:
                        raise DatosProductoInvalidos(
                            f"El campo '{campo}' no puede ser nulo."
                        )
                    setattr(producto, campo, valor)

            uow.productos.update(producto)
            if uow.session is not None:
                uow.session.expire(producto, ["categoria"])
            hidratado = uow.productos.get_activo_by_id(producto_id)
            assert hidratado is not None
            return ProductoRead.model_validate(hidratado)

    def update_stock(
        self, producto_id: int, data: ProductoStockUpdate
    ) -> ProductoRead:
        """Actualiza stock y disponibilidad de un producto activo."""
        if data.stock < 0:
            raise DatosProductoInvalidos("El stock del producto no puede ser negativo.")

        with self.uow as uow:
            producto = uow.productos.get_activo_by_id(producto_id)
            if producto is None:
                raise ProductoNoEncontrado(
                    f"Producto con id {producto_id} no encontrado."
                )

            producto.stock = data.stock
            producto.disponible = data.disponible
            uow.productos.update(producto)
            hidratado = uow.productos.get_activo_by_id(producto_id)
            assert hidratado is not None
            return ProductoRead.model_validate(hidratado)

    def delete_producto(self, producto_id: int) -> None:
        """Da de baja lógica un producto activo marcando ``activo = False``."""
        with self.uow as uow:
            producto = uow.productos.get_activo_by_id(producto_id)
            if producto is None:
                raise ProductoNoEncontrado(
                    f"Producto con id {producto_id} no encontrado."
                )

            producto.activo = False
            uow.productos.update(producto)

    listar_productos = list_productos
    obtener_producto = get_producto
    crear_producto = create_producto
    actualizar_producto = update_producto
    actualizar_stock = update_stock
    eliminar_producto = delete_producto


__all__ = [
    "CategoriaNoEncontrada",
    "DatosProductoInvalidos",
    "ProductoNoEncontrado",
    "ProductoNoEncontradoError",
    "ProductoService",
]
