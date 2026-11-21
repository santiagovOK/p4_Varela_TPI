"""Seed idempotente TPI para Food Store (E1.3 / CE-04).

Consigna TPI (docs/consignas_tpi.md):
- Invocable directamente de forma manual mediante ``python -m app.db.seed`` sin
  depender de ``setup.sh``.
- Inicializa el esquema si la base está vacía (``create_all_tables``).
- Crea de forma idempotente el usuario administrador (``admin`` / ``Admin1234!``,
  rol ``admin``), al menos 3 categorías activas y al menos 8 productos activos con
  stock positivo.
"""

from sqlalchemy.engine import Engine
from sqlmodel import Session, or_, select

from app.core.database import create_all_tables, engine
from app.core.security import hash_password
from app.modules.categorias.models import Categoria
from app.modules.productos.models import Producto
from app.modules.usuarios.models import Usuario

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin1234!"
ADMIN_EMAIL = "admin@foodstore.local"
ADMIN_FULL_NAME = "Administrador Food Store"
ADMIN_ROLE = "admin"

SEED_CATEGORIAS: tuple[dict[str, str], ...] = (
    {
        "nombre": "Hamburguesas",
        "descripcion": "Hamburguesas caseras a la parrilla con medallones de carne seleccionada.",
    },
    {
        "nombre": "Pizzas",
        "descripcion": "Pizzas a la piedra con muzzarella y masa de fermentación lenta.",
    },
    {
        "nombre": "Empanadas",
        "descripcion": "Empanadas horneadas y fritas con rellenos tradicionales.",
    },
    {
        "nombre": "Bebidas",
        "descripcion": "Gaseosas, aguas saborizadas y bebidas sin alcohol bien frías.",
    },
)

# Activos estáticos servidos desde `foodstore-frontend/public/img/<slug>.jpg` (E8.2).
SEED_PRODUCTOS: tuple[dict[str, object], ...] = (
    {
        "nombre": "Hamburguesa Clásica",
        "descripcion": "Medallón vacuno, queso cheddar, lechuga, tomate y salsa especial.",
        "precio_base": 8500.0,
        "imagen_url": "/img/hamburguesa-clasica.jpg",
        "stock": 25,
        "categoria": "Hamburguesas",
    },
    {
        "nombre": "Hamburguesa Doble Bacon",
        "descripcion": "Doble medallón, doble cheddar, panceta crocante y cebolla caramelizada.",
        "precio_base": 10900.0,
        "imagen_url": "/img/hamburguesa-doble-bacon.jpg",
        "stock": 20,
        "categoria": "Hamburguesas",
    },
    {
        "nombre": "Pizza Muzzarella",
        "descripcion": "Salsa de tomate casera, abundante muzzarella y aceitunas verdes.",
        "precio_base": 9200.0,
        "imagen_url": "/img/pizza-muzzarella.jpg",
        "stock": 18,
        "categoria": "Pizzas",
    },
    {
        "nombre": "Pizza Napolitana",
        "descripcion": "Muzzarella, rodajas de tomate fresco, ajo y albahaca.",
        "precio_base": 10200.0,
        "imagen_url": "/img/pizza-napolitana.jpg",
        "stock": 15,
        "categoria": "Pizzas",
    },
    {
        "nombre": "Empanada de Carne Cortada a Cuchillo",
        "descripcion": "Relleno tradicional de carne vacuna, cebolla, morrón y huevo.",
        "precio_base": 1600.0,
        "imagen_url": "/img/empanada-carne.jpg",
        "stock": 45,
        "categoria": "Empanadas",
    },
    {
        "nombre": "Empanada de Jamón y Queso",
        "descripcion": "Jamón cocido seleccionado y queso muzzarella fundido al horno.",
        "precio_base": 1500.0,
        "imagen_url": "/img/empanada-jamon-queso.jpg",
        "stock": 40,
        "categoria": "Empanadas",
    },
    {
        "nombre": "Gaseosa Cola 500ml",
        "descripcion": "Botella individual de gaseosa Cola 500ml.",
        "precio_base": 2400.0,
        "imagen_url": "/img/gaseosa-cola-500.jpg",
        "stock": 50,
        "categoria": "Bebidas",
    },
    {
        "nombre": "Agua Mineral sin Gas 500ml",
        "descripcion": "Agua mineral natural sin gas en botella de 500 ml.",
        "precio_base": 1800.0,
        "imagen_url": "/img/agua-mineral-500.jpg",
        "stock": 50,
        "categoria": "Bebidas",
    },
)


def _seed_in_session(session: Session) -> dict[str, int]:
    """Ejecuta la carga idempotente de admin, categorías y productos en una sesión."""
    creados = {"usuarios": 0, "categorias": 0, "productos": 0}

    admin = session.exec(
        select(Usuario).where(
            or_(
                Usuario.username == ADMIN_USERNAME,
                Usuario.email == ADMIN_EMAIL,
            )
        )
    ).first()
    if admin is None:
        admin = Usuario(
            username=ADMIN_USERNAME,
            full_name=ADMIN_FULL_NAME,
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            role=ADMIN_ROLE,
            disabled=False,
        )
        session.add(admin)
        creados["usuarios"] += 1
    else:
        admin.role = ADMIN_ROLE
        admin.disabled = False

    categorias_map: dict[str, Categoria] = {}
    for item in SEED_CATEGORIAS:
        categoria = session.exec(
            select(Categoria).where(Categoria.nombre == item["nombre"])
        ).first()
        if categoria is None:
            categoria = Categoria(
                nombre=item["nombre"],
                descripcion=item["descripcion"],
                activo=True,
            )
            session.add(categoria)
            creados["categorias"] += 1
        elif not categoria.activo:
            categoria.activo = True
        categorias_map[item["nombre"]] = categoria

    session.flush()

    for item in SEED_PRODUCTOS:
        nombre = str(item["nombre"])
        categoria_nombre = str(item["categoria"])
        categoria = categorias_map[categoria_nombre]
        assert categoria.id is not None

        producto = session.exec(
            select(Producto).where(Producto.nombre == nombre)
        ).first()
        if producto is None:
            producto = Producto(
                nombre=nombre,
                descripcion=str(item["descripcion"]),
                precio_base=float(item["precio_base"]),  # type: ignore[arg-type]
                imagen_url=str(item["imagen_url"]),
                stock=int(item["stock"]),  # type: ignore[arg-type]
                disponible=True,
                activo=True,
                categoria_id=categoria.id,
            )
            session.add(producto)
            creados["productos"] += 1
        else:
            if producto.stock <= 0:
                producto.stock = int(item["stock"])  # type: ignore[arg-type]
            if not producto.disponible:
                producto.disponible = True
            if not producto.activo:
                producto.activo = True
            if not producto.imagen_url or producto.imagen_url.startswith(
                "https://cdn.foodstore.local/img/"
            ):
                producto.imagen_url = str(item["imagen_url"])

    session.commit()
    return creados


def seed(session_or_engine: Session | Engine | None = None) -> dict[str, int]:
    """Inicializa tablas si faltan y ejecuta el seed idempotente de Food Store.

    Acepta opcionalmente una ``Session`` activa (por ejemplo desde CI), un ``Engine``
    (para pruebas aisladas) o ``None`` para usar el ``engine`` configurado.
    """
    if isinstance(session_or_engine, Session):
        bind = session_or_engine.get_bind()
        if isinstance(bind, Engine):
            create_all_tables(bind)
        return _seed_in_session(session_or_engine)

    target_engine = session_or_engine if session_or_engine is not None else engine
    create_all_tables(target_engine)
    with Session(target_engine, expire_on_commit=False) as session:
        return _seed_in_session(session)


run_seed = seed


if __name__ == "__main__":
    resultado = seed()
    print(
        "Seed Food Store completado: "
        f"usuarios={resultado['usuarios']}, "
        f"categorias={resultado['categorias']}, "
        f"productos={resultado['productos']}"
    )
