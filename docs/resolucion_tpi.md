# Trabajo Práctico Integrador — Food Store: Sistema de pedidos de comida
> **Estrategia de ejecución:** bottom-up dentro de cada incremento vertical, con un walking skeleton temprano y montaje progresivo. Primero se conecta un recorrido de catálogo entre base de datos, Repository/UoW, Service, API y frontend; después se incorporan sesión, administración, compra y cancelación. Cada incremento se integra y verifica antes de ampliar el siguiente; no se espera a terminar todo el backend para comenzar el frontend.

> **Materia:** Programación 4. 

> **Estados:** `[PENDIENTE]`, `[EN CURSO]`, `[COMPLETADA]`. E0.1–E0.3 corresponden al replanteo documental y de seguimiento y están completadas; E1–E10 siguen pendientes de implementación/integración TPI. La base heredada de los TPs de Unidad 9 y Unidad 10 es el punto de partida técnico del repositorio tras la limpieza de artefactos exclusivos del segundo parcial.

## 1. Propósito, punto de partida y alcance

El objetivo normativo es el **Trabajo Práctico Integrador — Food Store: Sistema de pedidos de comida**, una aplicación web para clientes y administración, según [consigna TPI](consignas_tpi.md) y [modelo UML TPI](tpi_UML_Food_Store.svg). El PDF fuente es `docs/consignas_tpi.pdf`; ambos documentos normativos cubren el dominio y el modelo objetivo.

El repositorio separa `foodstore-backend/` y `foodstore-frontend/` como proyectos independientes comunicados por HTTP. El punto de partida técnico asume **la base heredada de los TPs de Unidad 9 y Unidad 10** (ya finalizados al iniciar el TPI), junto con la limpieza de código y contratos exclusivos del segundo parcial (unidades de medida, relación N:N `ProductoCategoria`, `stock_cantidad`, `hay_stock`, `anulado_at`).

### 1.1 Qué viene de base desde TP9 y TP10, qué se adapta y qué se construye nuevo

| Categoría | Componentes y capacidades | Tareas vinculadas |
|---|---|---|
| **Base heredada (TP9 / TP10)** | **Backend (`unidad9_backend`):** módulo unificado `app/modules/usuarios/` (`model.py`, `schema.py`, `repository.py`, `unit_of_work.py`, `service.py`, `router.py`, `dependencies.py`), hash `bcrypt==5.0.0`, `PyJWT==2.15.1`, cookie `access_token` HttpOnly, `BaseRepository` (`app/core/repository.py`) y `UnitOfWorkBase` (`app/core/unit_of_work.py`), `Settings` inicial (`DATABASE_URL`, `SECRET_KEY`), CORS con `allow_credentials=True` y suite `pytest` (`StaticPool` en `tests/`). **Frontend (`unidad9_frontend`):** `src/api/axiosInstance.ts` con `withCredentials: true`, `setUnauthorizedHandler`, normalización `detail` y preservación de `error.cause`; `src/store/authStore.ts` con `persist` + `partialize` solo de identidad (`user`, nunca JWT), `login` (`URLSearchParams` + `/auth/me`), `checkSession` y `logout` con `try/finally`; `ProtectedRoute`; `LoginPage` y `RegisterPage` con `@tanstack/react-form`; `UnauthorizedPage`; `AdminUsersPage`; TanStack Query/Table, Zustand 5, Tailwind 4 y tests Vitest (`src/test/`). | E1.1–E1.2, E3.1, E4.1–E4.4, E7.1–E7.2, E8.1, E9.4 |
| **Se adapta / migra** | **Dominio y limpieza:** retiro de ingredientes y artefactos del segundo parcial (`unidades_medida`, relación N:N `ProductoCategoria`, `anulado_at`, `stock_cantidad`, `hay_stock`, `seed_unidades_medida`). **Backend estructura y seguridad:** separación de `app/core/{security,deps}.py`, `app/core/database.py` y `app/core/base_repository.py` más `app/modules/auth/` y `app/modules/usuarios/`; migración a `passlib[bcrypt]==1.7.4`, `bcrypt==4.0.1`, `python-jose[cryptography]==3.5.0` (claims `sub`, `role`, `type="access"`, `exp`) y `python-multipart==0.0.20`; ampliación de `Settings` (`ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `FRONTEND_ORIGIN`) y CORS explícito desde `settings.FRONTEND_ORIGIN`; `OAuth2PasswordBearerWithCookie` y `require_role` devolviendo `UserPublic`; `Usuario` con `created_at` y relación `pedidos`; `UserPublic` unificado de 7 campos y `UserCreate.password` con `max_length=72`; `/api/v1/auth/token` respondiendo `{"message": "Login exitoso"}`; `/api/v1/admin/usuarios` fuera de `/auth`, listando sin ocultar desactivados y bloqueando con 400 la auto-desactivación; `UnitOfWork` con `Session(engine, expire_on_commit=False)` y `Modelo.model_validate(...)` dentro del `with` en `usuarios`, `categorias`, `productos` y `pedidos` (excepciones de dominio en Service traducidas a HTTP en Router). **Catálogo:** lecturas `GET` públicas activas y paginación `{total, items}` (`limit` hasta 100); escrituras solo `admin`. **Frontend estructura y migración:** migración de carpetas planas (`src/{api,components,pages,services,store,types}/`) y features heredadas en inglés a los 5 dominios TPI en español bajo `src/features/{auth,categorias,productos,usuarios,pedidos}/` (barrel exports `index.ts`), `src/shared/{api,ui,components,layout}/`, `src/store/{authStore,cartStore}.ts` y `src/routes/{AppRouter,ProtectedRoute}.tsx` con alias dual `@/` (`vite.config.ts` y `tsconfig.app.json`); extracción de `src/shared/api/{axiosInstance,handleApiError,queryClient}.ts` (retirando `src/services/api.ts`), `timeout: 15_000`, `VITE_API_URL` con `/api/v1` y disparo de `setUnauthorizedHandler` también en `400` `"Cuenta de usuario desactivada"` (`403` nunca limpia sesión); adaptación de `authStore` a campos TPI (`usuario`, `cargando`, selectores atómicos/`useShallow`, `persist`+`partialize` solo `usuario`), `ProtectedRoute` con `<Outlet />`, `LoginPage` redirigiendo a `location.state?.from?.pathname ?? '/'`, `UnauthorizedPage` con enlace a `'/'`, `RegisterPage` vía capa `api/` + hook Query, y `AdminUsuariosPage` con TanStack Query + TanStack Table ocultando `"Desactivar"` en la fila propia. | E1.1–E1.3, E2.1–E2.2, E3.1–E3.2, E4.1–E4.4, E5.1–E5.3, E7.1–E7.2, E8.1, E9.4 |
| **Se construye nuevo** | **Backend:** módulo `pedidos` con reglas `RN-01`..`RN-06`, máquina de 4 estados (`PENDIENTE`, `EN_PREPARACION`, `ENTREGADO`, `CANCELADO`), `PedidoUnitOfWork` con sesión compartida sobre productos, endpoint `/pedidos/resumen` (declarado antes de `/{id}`). **Frontend:** `cartStore` persistido, catálogo público en `/` con búsqueda/filtro/paginación remota, carrito y checkout con TanStack Form, vista *Mis pedidos* y detalle con cancelación, paneles admin (resumen, ABM categorías/productos, gestión de pedidos y usuarios) con TanStack Table (`limit=100`). | E2.2, E3.3, E6.1–E6.4, E7.3, E8.1–E9.4 |
| **Testing continuo y entrega** | Suites `pytest` + `TestClient` (`StaticPool`) y `Vitest` / Testing Library actúan como red de verificación en cada paso/corte (`H1`..`H5`), con carácter descartable al final del proyecto: permanecen activas hasta completar `E10.2` y recién se excluyen/limpian en `E10.3` para el armado del `.zip` final (`CE-01`). Asimismo, los manifiestos (`requirements.txt`, `package.json`, `.env.example`) y la guía manual de `README.md` mantienen el proyecto instalable y ejecutable directamente (`pip`/`uvicorn` y `pnpm install`/`build`/`dev`) en cada hito sin depender de `setup.sh`. | E0.2, E1.1–E1.3, E7.1, E10.1–E10.3 |

## 2. Modelo, estados, reglas e historias

### 2.1 Entidades y relaciones normativas

El UML define cinco tablas, claves enteras autoincrementales, montos `float` y fechas `datetime`. Rangos, longitudes y valores permitidos se validan en schema y Service; no se exige CHECK de base.

| Entidad | Campos y restricciones | Relaciones / ciclo de vida |
|---|---|---|
| `Usuario` | `id`, `username` único, `full_name`, `email` único, `hashed_password`, `role` (`user` o `admin`), `disabled` (default `false`), `created_at`. | `Usuario.pedidos` / `Pedido.usuario`; baja lógica por `disabled=true`. Registro público siempre crea `user`. |
| `Categoria` | `id`, `nombre` único (2–100 caracteres), `descripcion`, `activo` (default `true`). | `Categoria.productos` / `Producto.categoria`; baja lógica, no libera nombre ni oculta productos asociados. |
| `Producto` | `id`, `categoria_id` FK obligatoria, `nombre`, `descripcion`, `precio_base: float >= 0`, `imagen_url`, `stock: int >= 0` default 0, `disponible` default `true`, `activo` default `true`. | Una categoría por producto; una categoría agrupa cero o más productos. Baja lógica por `activo=false`. Se vende solo si activo, disponible y con stock suficiente. |
| `Pedido` | `id`, `usuario_id` FK, `estado` default `PENDIENTE`, `forma_pago` (`EFECTIVO` o `TRANSFERENCIA`), `direccion_entrega` (5–200 caracteres), `notas`, `total`, `created_at`, `updated_at`. | `Usuario.pedidos` / `Pedido.usuario`; `Pedido.items` / `DetallePedido.pedido`. No se borra: se cancela. Total fijo desde creación. |
| `DetallePedido` | `id`, `pedido_id` FK, `producto_id` FK, `cantidad: int >= 1`, `nombre_producto`, `precio_unitario`, `subtotal`. | `Producto.detalles` / `DetallePedido.producto`. Línea inmutable con snapshot de nombre y precio; `subtotal = precio_unitario × cantidad`. |

No son parte del contrato TPI las entidades ni atributos exclusivos del parcial o de ejercicios previos (unidades de medida, ingredientes, relación N:N `ProductoCategoria`, `stock_cantidad`, `hay_stock`, `es_principal` ni `anulado_at`). La estructura objetivo de módulos usa `models.py`, `schemas.py`, `repository.py`, `unit_of_work.py`, `service.py` y `router.py` en `usuarios`, `categorias`, `productos` y `pedidos` (y `router.py`, `service.py`, `schemas.py` en `auth/`). Las relaciones conservan los nombres exactos del UML (`Categoria.productos`/`Producto.categoria`, `Usuario.pedidos`/`Pedido.usuario`, `Pedido.items`/`DetallePedido.pedido`, `Producto.detalles`/`DetallePedido.producto`).

### 2.2 Máquina de estados y permisos

| Estado actual | Transiciones permitidas | Actor |
|---|---|---|
| `PENDIENTE` | `EN_PREPARACION`, `CANCELADO` | Admin avanza o cancela; cliente propietario cancela. |
| `EN_PREPARACION` | `ENTREGADO`, `CANCELADO` | Admin. |
| `ENTREGADO` | Ninguna; terminal. | — |
| `CANCELADO` | Ninguna; terminal. | — |

El mapa de transiciones se valida en el Service antes de modificar el pedido; transición inválida responde 400. Al cancelar se restituye stock en la misma transacción que cambia estado. Cliente solo ve/cancela sus pedidos y solo cancela en `PENDIENTE`; admin ve todos y puede avanzar/cancelar estados no terminales. Admin gestiona catálogo y usuarios, y puede crear pedidos con sesión. No puede desactivarse a sí mismo.

### 2.3 Reglas de negocio oficiales

| Regla | Contrato |
|---|---|
| **RN-01 — Crear pedido** | Debe incluir al menos un ítem y no repetir producto. Cada producto existe, está activo y disponible, y tiene stock suficiente. En una sola transacción se descuenta stock, se crea línea con copia de nombre/precio, se calculan subtotales y total y el pedido nace `PENDIENTE`. Si falla una validación no persiste pedido ni descuentos. |
| **RN-02 — Transiciones** | Solo se permiten las transiciones de la tabla; estado terminal no cambia. Transición inválida: 400. |
| **RN-03 — Cancelar** | Restituye stock de cada línea en la misma transacción que actualiza estado. |
| **RN-04 — Permisos** | Cliente solo consulta y cancela sus propios pedidos, solo desde `PENDIENTE`; admin consulta todos y puede avanzar o cancelar estados no terminales. |
| **RN-05 — Inmutabilidad** | Líneas y total no cambian tras creación. No hay endpoint para editar ni borrar pedidos. |
| **RN-06 — Datos del pedido** | `forma_pago` es `EFECTIVO` o `TRANSFERENCIA`; `direccion_entrega` tiene 5–200 caracteres. Validación en schema. |

### 2.4 Contratos API y errores

Todos los endpoints están bajo `/api/v1`; API documentada en `/docs` y `/redoc`. Lecturas de catálogo son públicas y devuelven registros activos; escrituras de categorías/productos solo admin. `PUT` de recursos es parcial. Listados paginados usan `{total, items}`, `skip=0`, `limit=20`, máximo 100. No se hereda el límite 50 ni arrays simples del parcial. Se declara `/pedidos/resumen` antes de `/{id}`.

| Área / operación | Contrato principal |
|---|---|
| Auth | Registro público 201; duplicado 409. Login por formulario OAuth2; JWT en cookie `access_token` HttpOnly (30 min por defecto), logout borra cookie, `/auth/me` devuelve perfil. Nunca incluir token en cuerpo ni exponer `hashed_password`. |
| Categorías | CRUD con lecturas públicas de activas, escrituras admin, nombre único de 2–100, baja lógica `DELETE` 204; inactiva/inexistente 404; nombre permanece reservado. |
| Productos | CRUD público de lectura y admin de escritura; filtros de búsqueda/categoría y paginación `{total,items}`. Schema usa categoría, precio/imagen y stock entero. `PATCH` de stock/disponibilidad, baja lógica `DELETE` 204. |
| Usuarios | Admin lista, activa y desactiva usuarios; inexistente 404; no puede auto-desactivarse (400). |
| Pedidos | POST autenticado crea 201 y líneas snapshot; lista paginada, detalle y cancelación según propietario/rol. Cambio de estado admin; resumen con conteos, `pedidos_hoy` e ingresos de pedidos `ENTREGADO`. Sin edición/borrado. |

| Método | Ruta `/api/v1` | Acceso | Éxito | Errores propios del endpoint |
|---|---|---|---|---|
| POST | `/api/v1/auth/register` | Público | 201 `UserPublic` | 409 username o email duplicado |
| POST | `/api/v1/auth/token` | Público | 200 `{message: "Login exitoso"}`; establece cookie | 401 credenciales incorrectas; 400 cuenta desactivada |
| POST | `/api/v1/auth/logout` | Público | 200; borra cookie | — |
| GET | `/api/v1/auth/me` | Sesión | 200 `UserPublic` | — |
| GET | `/api/v1/admin/usuarios` | Admin | 200 `list[UserPublic]` | — |
| POST | `/api/v1/admin/usuarios/{id}/activar` | Admin | 200 `UserPublic` | 404 |
| POST | `/api/v1/admin/usuarios/{id}/desactivar` | Admin | 200 `UserPublic` | 404; 400 si intenta desactivarse a sí mismo |
| GET | `/api/v1/categorias` | Público | 200 `list[CategoriaRead]` (activas) | — |
| GET | `/api/v1/categorias/{id}` | Público | 200 `CategoriaRead` | 404 |
| POST | `/api/v1/categorias` | Admin | 201 `CategoriaRead` | 409 |
| PUT | `/api/v1/categorias/{id}` | Admin | 200 `CategoriaRead` | 404, 409 |
| DELETE | `/api/v1/categorias/{id}` | Admin | 204 sin cuerpo | 404 |
| GET | `/api/v1/productos` | Público | 200 `ProductosPaginados` | — |
| GET | `/api/v1/productos/{id}` | Público | 200 `ProductoRead` | 404 |
| POST | `/api/v1/productos` | Admin | 201 `ProductoRead` | 404 si categoría inexistente o inactiva |
| PUT | `/api/v1/productos/{id}` | Admin | 200 `ProductoRead` | 404 producto inexistente o categoría nueva inexistente/inactiva |
| PATCH | `/api/v1/productos/{id}/stock` | Admin | 200 `ProductoRead` | 404 |
| DELETE | `/api/v1/productos/{id}` | Admin | 204 sin cuerpo | 404 |
| POST | `/api/v1/pedidos` | Sesión | 201 `PedidoRead` | 404 producto inexistente/inactivo; 400 stock insuficiente, no disponible o repetido |
| GET | `/api/v1/pedidos` | Sesión | 200 `PedidosPaginados` | — |
| GET | `/api/v1/pedidos/resumen` | Admin (declarar antes de `/{id}`) | 200 `ResumenPedidos` | — |
| GET | `/api/v1/pedidos/{id}` | Dueño o admin | 200 `PedidoRead` | 404; 403 pedido de otro usuario |
| PATCH | `/api/v1/pedidos/{id}/estado` | Admin | 200 `PedidoRead` | 404; 400 transición inválida |
| PATCH | `/api/v1/pedidos/{id}/cancelar` | Dueño | 200 `PedidoRead` | 404; 403 pedido ajeno; 400 si no está `PENDIENTE` |

Schemas de entrada y salida (campos omitidos en “Read” se agregan según se indica):

| Schema | Campos | Validación normativa |
|---|---|---|
| `UserCreate` | `username`, `full_name`, `email`, `password` | `password`: `Field(min_length=8, max_length=72)` (límite de 72 bytes UTF-8 de bcrypt) |
| `UserPublic` | `id`, `username`, `full_name`, `email`, `role`, `disabled`, `created_at` | No expone `hashed_password` |
| `CategoriaCreate` / `CategoriaUpdate` | `nombre`, `descripcion` | `nombre` de 2–100 caracteres; `CategoriaUpdate` parcial (`\| None = None`, `model_dump(exclude_unset=True)`) |
| `CategoriaRead` | Campos anteriores + `id`, `activo` | — |
| `ProductoCreate` / `ProductoUpdate` | `nombre`, `descripcion`, `precio_base`, `imagen_url`, `stock`, `disponible`, `categoria_id` | `precio_base >= 0`; `stock >= 0`; `ProductoUpdate` parcial (`\| None = None`, `model_dump(exclude_unset=True)`) |
| `ProductoRead` | Campos anteriores + `id`, `activo`, `categoria: CategoriaRead` | — |
| `ProductoStockUpdate` | `stock`, `disponible` | `stock >= 0` |
| `ProductosPaginados` | `total: int`, `items: list[ProductoRead]` | — |
| `ItemPedidoCreate` | `producto_id`, `cantidad` | `cantidad >= 1` |
| `PedidoCreate` | `items: list[ItemPedidoCreate]`, `forma_pago`, `direccion_entrega`, `notas` | Mínimo 1 ítem; pago `EFECTIVO` o `TRANSFERENCIA`; dirección 5–200 caracteres |
| `DetallePedidoRead` | `producto_id`, `nombre_producto`, `precio_unitario`, `cantidad`, `subtotal` | — |
| `PedidoRead` | `id`, `usuario_id`, `estado`, `forma_pago`, `direccion_entrega`, `notas`, `total`, `created_at`, `updated_at`, `items: list[DetallePedidoRead]` | — |
| `PedidosPaginados` | `total`, `items: list[PedidoRead]` | — |
| `CambioEstado` | `estado` | Uno de los cuatro estados |
| `ResumenPedidos` | `pendientes`, `en_preparacion`, `entregados`, `cancelados`, `pedidos_hoy`, `ingresos_entregados` | Conteos con `func.count`; ingresos suma `total` de pedidos `ENTREGADO` |

Todos los schemas son SQLModel sin `table=True`; los de lectura se validan con `Modelo.model_validate(objeto)` dentro del bloque `with` del Unit of Work, y nunca se responde con un modelo de tabla. Los errores comunes de sesión, autorización y validación (`401` desde `get_current_user`, `400` `"Cuenta de usuario desactivada"` desde `get_current_active_user` o login, `403` desde `require_role` y `422` de FastAPI) se describen a continuación y no se repiten como errores propios de cada endpoint.

Errores se exponen mediante `HTTPException` con `detail`. El Service lanza excepciones de dominio y el Router las traduce a HTTP (`auth` y `usuarios` pueden lanzar `HTTPException` desde el Service):

| Excepción de dominio | Código HTTP | Cuándo se produce |
|---|---|---|
| `CategoriaNoEncontrada`, `ProductoNoEncontrado`, `PedidoNoEncontrado`, `UsuarioNoEncontrado` | `404` | Registro inexistente o dado de baja lógica. |
| `NombreDuplicado`, `UsuarioDuplicado` | `409` | Nombre de categoría, `username` o `email` ya existente. |
| `PedidoAjeno` | `403` | Cliente intenta consultar o cancelar un pedido de otro usuario. |
| `StockInsuficiente`, `ProductoNoDisponible`, `ProductoRepetido`, `TransicionInvalida` | `400` | Violación de reglas RN-01 a RN-03 o auto-desactivación de admin. |

La creación transaccional no persiste nada si falla; por ejemplo, con dos líneas cuya segunda no tiene stock, tampoco persisten la primera línea ni su descuento.

### 2.5 Historias internas (no oficiales)

| ID | Historia | Tareas vinculadas |
|---|---|---|
| HU-TPI-01 | Autenticación, sesión y rutas protegidas por rol. | E4.1–E4.4, E7.2, E8.1 |
| HU-TPI-02 | Catálogo público, búsqueda, filtros y carrito persistido. | E7.3, E8.2–E8.3 |
| HU-TPI-03 | Checkout, compra y consulta/cancelación de pedidos propios. | E6.1–E6.3, E8.3–E8.4 |
| HU-TPI-04 | Administración de categorías, productos y stock. | E5.1–E5.3, E9.2 |
| HU-TPI-05 | Administración de pedidos, transiciones y resumen. | E6.2, E6.4, E9.1, E9.3 |
| HU-TPI-06 | Gestión administrativa de usuarios. | E4.4, E9.4 |

## 3. Lineamientos técnicos

### 3.1 Backend objetivo

FastAPI + SQLModel sobre PostgreSQL con prefijo `/api/v1` y documentación en `/docs` y `/redoc`.

- **Estructura exacta de archivos**: `app/main.py`, núcleo compartido `app/core/{config,database,security,deps,unit_of_work,base_repository}.py`, módulos `app/modules/{auth,usuarios,categorias,productos,pedidos}/` (`auth/` con `router.py`, `service.py`, `schemas.py`; los cuatro módulos de dominio con `models.py`, `schemas.py`, `repository.py`, `unit_of_work.py`, `service.py`, `router.py`) y `app/db/seed.py`. Respecto de `unidad9_backend`, se desdobla el módulo unificado `usuarios/` en `app/core/{security,deps}.py`, `app/modules/auth/` y `app/modules/usuarios/`, se traslada `app/database.py` a `app/core/database.py` y se renombra `app/core/repository.py` a `app/core/base_repository.py`.
- **Configuración y CORS (`config.py`, `main.py`)**: `Settings(BaseSettings)` con `pydantic-settings`, `SECRET_KEY: str = Field(min_length=32)`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `DATABASE_URL` y `FRONTEND_ORIGIN` (ampliando el `config.py` de TP9, que solo define `database_url`, `secret_key` y flags de test). Middleware CORS con `allow_origins=[settings.FRONTEND_ORIGIN]` (reemplazando los orígenes fijos de TP9; nunca `"*"`) y `allow_credentials=True`. `main.py` monta todos los routers bajo `/api/v1` (sacando `/admin/usuarios` fuera de `/auth`) y retira `seed_unidades_medida`/`seed_test_admin` del `lifespan`.
- **Capas, UoW y Repositorios**: Router valida transporte, obtiene Service con `Depends` y traduce excepciones de dominio; nunca abre UoW ni llama `session.commit()`. `UnitOfWork` (migrado desde `UnitOfWorkBase` de TP9) abre `Session(engine, expire_on_commit=False)` en `__enter__` y ejecuta `commit()`/`rollback()` y `close()` en `__exit__`. Los Services abren `with self.uow as uow:`, aplican reglas y convierten/devuelven schemas con `Modelo.model_validate(objeto)` dentro del bloque `with`. Schemas `*Update` (`CategoriaUpdate`, `ProductoUpdate`) son parciales (`| None = None`) y se aplican con `model_dump(exclude_unset=True)`. `BaseRepository[T]` expone `get_by_id`, `get_all`, `add`, `delete`; repositorios de dominio implementan `get_by_username` y `get_by_email` (`usuarios`), `get_by_nombre` (`categorias`), `search` (`productos`, por nombre, categoría y disponible), y `list_by_usuario` y `count_by_estado` (`pedidos`). `PedidoUnitOfWork` comparte la sesión entre `pedidos` y `productos`.
- **Seguridad (`security.py`, `deps.py`)**: migración desde `bcrypt==5.0.0` + `PyJWT==2.15.1` de TP9 hacia `passlib[bcrypt]==1.7.4` + `bcrypt==4.0.1` y `python-jose[cryptography]==3.5.0`, con límite de 72 bytes UTF-8 validado en `UserCreate.password` (`Field(min_length=8, max_length=72)`). `OAuth2PasswordBearerWithCookie` (reemplaza el parámetro `Cookie()` directo de TP9) extrae el JWT exclusivamente de la cookie HttpOnly `access_token` (rechaza `Authorization: Bearer`), emitida y borrada con `httponly=True` y `samesite="lax"`. Claims JWT obligatorios: `sub`, `role`, `type="access"`, `exp`. Cadena jerárquica: `get_current_user` (consulta autoritativa en PostgreSQL en cada request por `username` indexado; 401 si falta cookie, token inválido/expirado, `type != "access"` o usuario inexistente) → `get_current_active_user` (400 `"Cuenta de usuario desactivada"` si `disabled=True`) → `require_role(allowed_roles)` (devuelve `UserPublic` de 7 campos; 403 si `current_user.role not in allowed_roles`), aplicando bajas o cambios de estado de inmediato. `/api/v1/auth/token` responde `{"message": "Login exitoso"}`, `/api/v1/admin/usuarios` lista todas las cuentas sin ocultar desactivadas por defecto y `/api/v1/admin/usuarios/{id}/desactivar` bloquea con `400` la auto-desactivación. Prevención de escalamiento horizontal (IDOR) combinada con RBAC en pedidos (`pedido.usuario_id == current_user.id` -> `PedidoAjeno` 403 en `RN-04`).
- **Seed TPI (`app/db/seed.py`)**: idempotente mediante `python -m app.db.seed`: admin `admin` / `Admin1234!`, rol `admin`, al menos 3 categorías y 8 productos con stock. Esto es objetivo E1.3, no comportamiento actual.

### 3.2 Frontend objetivo

React + TypeScript estricto (`strict: true`, sin `any`).

- **Estructura exacta de archivos**: migración desde la estructura plana de TP9 (`src/{api,components,pages,services,store,types}/`, sin alias `@/`) hacia `src/shared/{api,ui,components,layout}/` (`axiosInstance.ts`, `handleApiError.ts`, `queryClient.ts`; `Button`, `Card`, `Input`, `Modal`, `BadgeEstado`; `Paginacion`, `Skeleton`, `EstadoVacio`, `EstadoError`; `Navbar`, `MainLayout`), `src/features/{auth,categorias,productos,usuarios,pedidos}/` (cada una con `pages/`, `components/`, `hooks/`, `api/`, `types/` y barrel export `index.ts`, usando alias `@/`), `src/store/{authStore,cartStore}.ts`, `src/routes/{AppRouter,ProtectedRoute}.tsx` (`ProtectedRoute` con `Outlet`), `src/App.tsx`, `src/main.tsx` y `src/index.css`. Reglas de frontera de barrel exports (`index.ts`): (a) solo exports explícitos con nombre (nunca `export *`); (b) todo import desde fuera de una feature (`routes/`, `shared/` u otra feature) debe importar desde el barrel público `@/features/<dominio>` y nunca desde subcarpetas internas; (c) dentro de una misma feature, los archivos internos usan rutas relativas y nunca importan desde su propio `index.ts` para evitar ciclos en Vite. Configuración dual del alias `@/` (`RA-08`): `vite.config.ts` (`resolve.alias` apuntando `@` a `path.resolve(import.meta.dirname, "src")` con `@types/node` en `devDependencies`) y `tsconfig.app.json` (`"compilerOptions": { "paths": { "@/*": ["./src/*"] } }`).
- **Axios y errores (`axiosInstance.ts`, `handleApiError.ts`)**: instancia única tomada de `unidad9_frontend/src/api/axiosInstance.ts` (que ya incluye `withCredentials: true`, `setUnauthorizedHandler` y `error.cause`) y adaptada a `src/shared/api/` con `baseURL = VITE_API_URL` (`http://localhost:8000/api/v1` frente al `http://localhost:8000` de TP9), `timeout: 15_000` y retiro de `src/services/api.ts`. Login envía formulario `application/x-www-form-urlencoded` vía `URLSearchParams` a `POST /auth/token` seguido de `GET /auth/me`. Manejo diferenciado `401`/`400` vs `403`: callback desacoplado `setUnauthorizedHandler` (evita ciclos de importación entre Axios y store) limpia `authStore` ante `401` (fuera de `/auth/token` y `/auth/me`) y amplía el comportamiento de TP9 para limpiar también ante `400` (`"Cuenta de usuario desactivada"`) sin usar `window.location.href`; `403 Forbidden` nunca cierra sesión ni limpia `authStore` y es propagado por `handleApiError.ts`, que normaliza `detail` (string o array 422 de FastAPI) en `Error` preservando `error.cause` con el `AxiosError` original. `pages/` y `components/` no invocan `axiosInstance` directamente sino mediante `features/<dominio>/api/` + TanStack Query en `features/<dominio>/hooks/` (`RA-07`).
- **Estado y sesión (TanStack Query + Zustand 5)**: TanStack Query 5 con custom hooks por feature para estado remoto e invalidación; TanStack Form 1 (ya probado en `LoginPage`/`RegisterPage` de TP9) para formularios; TanStack Table 8 para tablas admin (paginación local sobre `limit=100`; catálogo público pagina en servidor). Composición raíz: `main.tsx` monta `QueryClientProvider` con `src/shared/api/queryClient.ts` y registra el handler de `axiosInstance`; `App.tsx` (sin lógica de negocio ni queries) ejecuta `checkSession()` en `useEffect` al montar y renderiza `<AppRouter />`. Zustand 5 con selectores atómicos y `useShallow` (`zustand/react/shallow`); `authStore` en `src/store/authStore.ts` parte del store TP9 (`persist` + `partialize` solo de identidad y `logout` `try/finally`) adaptándolo a campos TPI (`usuario`, `cargando`, nunca JWT ni flags volátiles), y `cartStore` persiste el carrito. `checkSession()` es la única llamada de sesión permitida en `useEffect` al montar `App.tsx` (evita estado zombie de identidad persistida). `logout()` usa `try/finally` para llamar a `POST /auth/logout` y limpiar el estado local incondicionalmente. Orden estricto en `ProtectedRoute.tsx` (migrado desde `children` de TP9 a `<Outlet />`): (1) `cargando === true` muestra indicador accesible sin redirigir tras F5; (2) `!usuario` redirige con `<Navigate to="/login" replace state={{ from: location }} />`; (3) `allowedRoles` definido y sin `usuario.role` redirige con `<Navigate to="/unauthorized" replace />`; (4) de lo contrario renderiza `<Outlet />`. `LoginPage` redirige tras login exitoso a `location.state?.from?.pathname ?? "/"`, `UnauthorizedPage` enlaza a `"/"`, y `AdminUsuariosPage` usa TanStack Query + TanStack Table ocultando `"Desactivar"` en la fila propia. `VITE_API_URL` apunta a `http://localhost:8000/api/v1`.
- **Estilos, diseño responsive y accesibilidad (Tailwind CSS 4)**: `src/index.css` parte de `@import "tailwindcss";` preservando la paleta visual del parcial (`slate` para superficies/bordes/textos, `blue`/`indigo` para acciones principales y acentos, y semánticos `emerald`/`amber`/`rose` para estados de `BadgeEstado`, stock y errores). Diseño **mobile-first** y responsive (`sm:`, `md:`, `lg:`) con foco visible (`focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2`), semántica ARIA (`aria-label`, `aria-invalid`, `aria-describedby`, `aria-busy`, `aria-live`, `aria-modal`, `role="alert"/"status"/"dialog"`) y contraste accesible en todos los componentes de `src/shared/ui/` y pantallas.

### 3.3 Versiones y configuración objetivo

Versiones normativas, no instaladas/fijadas en esta actualización (contrastadas frente a TP9): Python 3.11–3.13; PostgreSQL ≥15; `fastapi[standard]>=0.115`; `sqlmodel>=0.0.22`; `psycopg2-binary` 2.9; `python-jose[cryptography]==3.5.0` (TP9 usa `PyJWT==2.15.1`), `passlib[bcrypt]==1.7.4` y `bcrypt==4.0.1` (TP9 usa `bcrypt==5.0.0`), `pydantic-settings` 2.x, `python-multipart==0.0.20` (TP9 usa `0.0.34`). Frontend: Node ≥20.19, React 19 (`^19.0.0`), TypeScript ≥5.9 (TP9 usa `~5.7.2`), Vite ≥7 (TP9 usa `^6.2.0`), Tailwind 4 (`@tailwindcss/vite`), TanStack Query 5 (`^5.66.0`), Form 1 (`1.33.5`), Table 8 (`^8.21.3`), React Router DOM 7 (`^7.1.5`, `BrowserRouter`), Zustand 5 (`^5.1.0`), Axios 1 (`^1.21.1`), Vitest (`^3.2.7`), pnpm ≥9. Fijar combinaciones exactas compatibles es E1.1/E7.1.

| Variable objetivo | Uso |
|---|---|
| `DATABASE_URL` | PostgreSQL; desarrollo local puede usar SQLite. |
| `SECRET_KEY` | Firma JWT, mínimo 32 caracteres (`Field(min_length=32)`). |
| `ALGORITHM` | Algoritmo JWT; ejemplo `HS256` (en TP9 está fijo como constante en `usuarios/service.py`). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración, valor por defecto 30 (en TP9 está fijo como constante en `usuarios/service.py`). |
| `FRONTEND_ORIGIN` | Origen CORS explícito, por ejemplo `http://localhost:5173` (en TP9 los orígenes están fijos en `main.py`). |
| `VITE_API_URL` | Base Axios objetivo incluye `/api/v1` (`http://localhost:8000/api/v1`); en TP9 toma `http://localhost:8000` por defecto. |

### 3.4 Base heredada, testing continuo e infraestructura

El punto de partida combina **la base heredada real de TP9** (`unidad9_backend`: módulo unificado `usuarios`, cookie `access_token` HttpOnly, `bcrypt==5.0.0`, `PyJWT==2.15.1`, CORS con credenciales, `BaseRepository`/`UnitOfWorkBase`; `unidad9_frontend`: `axiosInstance.ts` con `withCredentials`, `setUnauthorizedHandler` y `error.cause`, `authStore.ts` con `persist`+`partialize` y `logout` `try/finally`, `ProtectedRoute`, `LoginPage`/`RegisterPage` con `@tanstack/react-form`, `UnauthorizedPage` y `AdminUsersPage`) con la limpieza de los artefactos exclusivos del segundo parcial (`unidades_medida`, `ProductoCategoria`, `stock_cantidad`, `hay_stock`, `anulado_at`, `seed_unidades_medida`) y de ingredientes.

El testing continuo ya probado en TP9 (`unidad9_backend/tests/` con `pytest` + `ASGITransport`/`TestClient` y `StaticPool` sobre SQLite en memoria; `unidad9_frontend/src/test/` con `Vitest` + Testing Library sobre `axiosInstance`, `authStore`, `AppSession`, `ProtectedRoute`, `RegisterPage`, `AdminUsersPage` y `Navbar`) constituye el insumo base a migrar y refinar escalonadamente en cada corte de contrato (`H1`..`H5`) hacia `foodstore-backend/tests/` y `foodstore-frontend/src/__tests__/` sobre los módulos Food Store (`auth`, `usuarios`, `categorias`, `productos`, `pedidos`). Aunque las pruebas automatizadas no son requisito académico evaluado en la rúbrica, aportan evidencia proporcional en cada incremento.

- **(a) Ciclo de vida de la suite de pruebas:** `foodstore-backend/tests/` y `foodstore-frontend/src/__tests__/` (junto con sus cachés y coberturas, como `.pytest_cache/` y `coverage/`) se ejecutan y actualizan en cada incremento (`H1`..`H4`) y en `E10.2`; no se borrarán ni desactivarán prematuramente, y su exclusión o limpieza para el `.zip` de entrega final (`CE-01`) se realiza recién en `E10.3`.
- **(b) Autonomía del arranque manual frente a `setup.sh`:** `setup.sh` es una utilidad opcional; el proyecto no depende de `setup.sh` para configurar variables, crear tablas ni arrancar servicios. Desde `H1` y antes de `E10.1`, copiar `.env.example` a `.env` y ejecutar los comandos manuales normativos (`pip install -r requirements.txt`, `python -m app.db.seed` desde `E1.3`, `uvicorn app.main:app`, `pnpm install`, `pnpm build`, `pnpm dev`) levanta el sistema limpio sin errores (`CE-03`..`CE-06`).

### 3.5 Estrategia de ejecución e integración progresiva

Bottom-up significa construir cada recorrido desde modelos y persistencia hasta HTTP y UI, no completar horizontalmente todo el backend. Las épicas agrupan responsabilidades; los números de tarea y el orden del seguimiento local no son un orden topológico. `Dependencias` enumera condiciones de cierre de la tarea completa. Solo se inician porciones identificadas abajo cuando sus prerrequisitos reales están satisfechos. Una tarea parcialmente implementada queda `[EN CURSO]`, nunca `[COMPLETADA]`; los hitos no crean nuevas tareas ni IDs.

No se simulan APIs, repositorios ni permisos para declarar un hito logrado. No se montan routers, imports ni relaciones hacia módulos aún inexistentes. En H1 se integra la relación Categoria–Producto; `Producto.detalles` y los otros enlaces a pedidos se incorporan con E2.2, sin relaciones rotas ni entidades ficticias.

| Hito | Trabajo y condiciones concretas | Evidencia necesaria para avanzar |
|---|---|---|
| H1 — Walking skeleton público | Completar E1.1, E1.2, E2.1 (categoría/producto), E3.1, E3.2 y E7.1. Integrar solamente lecturas públicas de E5.1/E5.2, componentes de carga/vacío/error de E7.3 y primera pantalla de lectura de E8.2. Esas cuatro tareas permanecen en curso si falta su alcance completo. Usar datos reales de catálogo en BD de desarrollo; no depende del seed TPI, auth, entidades/API de pedidos ni E6.4. | Con PostgreSQL y navegador, un producto real atraviesa Repository/UoW → Service → API `/api/v1/productos` → Axios/Query → catálogo. Respuesta `{total,items}` y categoría coherentes, sin contrato N:N anterior. Cambiar el dato en BD y volver a consultar permite observarlo en pantalla. Comprobar también carga, vacío y error. Arranque manual limpio sin `setup.sh` y suite `pytest`/`Vitest` del corte en verde. |
| H2 — Catálogo completo y sesión | Completar E2.2, E4.1–E4.3, E5.1–E5.3, E1.3, E7.2/E7.3, E8.1/E8.2 y E9.2, respetando la matriz de cierre. E2.2 agrega modelos y relaciones de usuario/pedido/detalle, no exige todavía implementar sus operaciones. E1.3 exige su seed completo; no se declara terminado con datos manuales de H1. | Registro/login/logout y `/auth/me` reales; permisos de catálogo, búsqueda/filtros/paginación/carrito y ABM admin observables. Seed repetible con admin, ≥3 categorías y ≥8 productos; nombre de categoría no liberado tras baja y registros inactivos 404. Arranque manual limpio sin `setup.sh` (incluyendo `python -m app.db.seed`) y suite `pytest`/`Vitest` del corte en verde. |
| H3 — Compra y cancelación | Completar E3.3, E6.1–E6.3 y E8.3/E8.4 sobre H2. El resumen E6.4 no bloquea este recorrido. | Compra persistida con snapshots/total y stock descontado; lista/detalle propios y cancelación con restitución una sola vez. Caso de dos líneas, segunda sin stock: ni pedido ni descuento de la primera persisten. Error de checkout conserva formulario/carrito y no navega como éxito. Arranque manual limpio sin `setup.sh` y suite `pytest`/`Vitest` del corte en verde. |
| H4 — Administración restante | Completar E4.4, E6.4, E9.1, E9.3 y E9.4. Estas ramas pueden avanzar independientemente cuando sus dependencias reales estén disponibles; H3 no es una barrera artificial para el listado de usuarios. | Resumen, cambios de estado válidos/inválidos, permisos y activación/desactivación de usuarios verificados; no hay auto-desactivación. Arranque manual limpio sin `setup.sh` y suite `pytest`/`Vitest` del corte en verde. |
| H5 — Verificación y entrega | E10.1 verifica el sistema integrado (flujo levantado manualmente según `README.md` sin depender de `setup.sh`); E10.2 cierra la alineación de `setup.sh`/CI y ejecuta la última corrida integral de `pytest`/`Vitest`; E10.3 prepara la entrega y realiza la exclusión/limpieza de carpetas de pruebas en el `.zip` final (`CE-01`). | Evidencia actual por criterio, ejecución manual en máquina limpia sin `setup.sh`, última corrida integral `pytest`/`Vitest` en verde y entregables normativos (con exclusión de tests recién en `E10.3`). No reutilizar resultados anteriores ni llamar a esta etapa primera integración. |

Orden interno para evitar ambigüedades: H2 ejecuta E2.2 → E4.1 → E4.2 → E4.3 → E5.1 → E5.2 → E5.3; E1.3 puede completarse después de E5.2 y antes de verificar el ABM. La rama frontend E7.2 puede avanzar tras E4.3; E7.3 puede completarse en paralelo; luego E8.1/E8.2 y E9.2 cuando estén sus dependencias. No hay dependencia del catálogo respecto del seed: datos de desarrollo de H1 permiten comprobar lecturas antes de E1.3. En H3: E3.3 → E6.1 → E6.2 → E6.3 → E8.3 → E8.4. En H4: E4.4 → E9.4 es independiente de E6.4 → E9.1/E9.3.

Todo corte de contrato integra en la misma unidad backend, consumidores, imports, tipos y pruebas afectadas. Se elimina la vía obsoleta; no se crean adaptadores temporales ni se conservan endpoints N:N. El corte de catálogo H1 integra coordinadamente las porciones de E2.1/E3.2/E5.1/E5.2/E7.1/E8.2 necesarias para arrancar una aplicación real; no se publica como incremento ejecutable un modelo nuevo con consumidores antiguos rotos. Antes de integrar cada incremento, se comprueban arranque, recorrido vertical y checks existentes afectados. En ese mismo corte se actualizan comprobaciones de tablas/unidades/N:N obsoletas; no se saltan, desactivan ni dejan CI fallando hasta E10.2. E10.2 progresa dentro de cada corte y solo se cierra tras E10.1; su dependencia final no bloquea los cambios previos de automatización. En ningún corte previo a `E10.1` el arranque dependerá de `setup.sh`, ni se eliminarán o vaciarán las suites `pytest`/`Vitest` antes de `E10.3`. Aquí solo se documenta esa regla: no se edita setup/CI/aplicación ni se ejecutan sus procesos.

### 3.6 Buenas prácticas aplicables y aceptación transversal

La consigna TPI y UML determinan el contrato; ejemplos didácticos previos no modifican la categoría única ni las relaciones objetivo. Estas prácticas generales no obligan a nuevos diagramas, abstracciones, convenciones incompatibles ni expansión de pruebas fuera de la rúbrica.

- Controles, formularios y tablas utilizables con teclado, foco visible, labels asociados a entradas y encabezados semánticos en tablas; error y estado no se comunican solo mediante color.
- Diferenciar carga inicial, actualización, vacío, fallo y éxito. Skeleton decorativo oculto a tecnologías de asistencia; región ocupada y mensaje de estado comunican espera. Respetar movimiento reducido. Error relevante con texto comprensible y anuncio apropiado, no trazas.
- Ante error de actualización, conservar datos útiles visibles e identificarlos como previos; no presentar fallo como lista vacía ni datos obsoletos como recién confirmados.
- Errores esperables de formulario/mutación muestran feedback a partir de `detail`, conservan valores editables y permiten corregirlos. No exigir reintentos automáticos ni ofrecer recuperación sin acción real.
- Checkout fallido conserva carrito/formulario, sin redirección ni limpieza de éxito; login fallido no simula sesión confirmada. Acciones admin fallidas no muestran éxito ni confirman cambios rechazados; mantienen feedback visible.
- Query conserva estado remoto; Zustand persiste solo usuario/carrito según contrato. Filtros, página, modal y borradores/formularios quedan en estado local o TanStack Form, sin duplicar colecciones remotas ni persistir JWT.

E7.3 implementa las piezas compartidas; E8/E9 las ejercitan en recorridos reales. Las aceptaciones de estas tareas incorporan este gate transversal.

## 4. Épicas y tareas
La aceptación de cada tarea funcional incorpora el gate de integración progresiva de 3.5; las tareas de interfaz incorporan además las prácticas de 3.6. Cada tarea funcional aporta evidencia del recorrido afectado, no únicamente compilación.

Los archivos rotulados **objetivo pendiente** no se afirman existentes. El seguimiento local interno se mantiene como reflejo del plan; no se sincroniza ningún tablero remoto. Cada tarea tiene acción, dependencias, archivos, alcance, vínculos normativos, aceptación, estado y evidencia.

### Épica 0 — Definición y preparación documental

#### E0.1 — Formalizar contrato y trazabilidad TPI
- **Acción:** definir fuentes, modelo, brechas, contratos, rúbrica y trazabilidad en esta resolución.
- **Dependencias:** —.
- **Archivos:** `docs/resolucion_tpi.md`; `docs/consignas_tpi.md`; `docs/tpi_UML_Food_Store.svg`.
- **Consigna/alcance:** fuente normativa y plan, sin implementar aplicación.
- **RN/HU:** RN-01–06; HU-TPI-01–06.
- **Criterio de aceptación:** están cubiertos los diez criterios, siete entregables, seis RN y 36 tareas con estados no inflados.
- **Estado:** [COMPLETADA].
- **Evidencia:** se contrastaron las fuentes, contratos, criterios de evaluación, siete entregables, seis RN y 36 tareas con sus estados.

#### E0.2 — Actualizar identidad, README y guía operativa
- **Acción:** alinear identidad y documentación operativa, estableciendo la guía manual (Opción B de `README.md`) como camino normativo autónomo (`CE-02`, `CE-05`, `CE-06`) y `setup.sh` como utilidad auxiliar opcional, preservando cómo corre hoy el catálogo.
- **Dependencias:** E0.1.
- **Archivos:** `README.md`, `foodstore-backend/README.md`, `foodstore-frontend/README.md`, `package.json`, `setup.sh`, `.github/workflows/ci.yml`, `.env.example` de cada subproyecto.
- **Consigna/alcance:** guía manual autónoma de base heredada y objetivo TPI pendiente sin depender de `setup.sh`; no cambiar comportamiento.
- **RN/HU:** HU-TPI-01–06 como objetivos, no evidencia.
- **Criterio de aceptación:** enlaces existentes y comandos manuales normativos distinguidos de tareas futuras; Opción B de `README.md` documentada como camino autónomo (`CE-02`, `CE-05`, `CE-06`) y `setup.sh` como auxiliar opcional.
- **Estado:** [COMPLETADA].
- **Evidencia:** README y enlaces verificados; configuración/identidad revisadas y `setup.sh --help` comprobado. Ejecución de máquina limpia pendiente.

#### E0.3 — Alinear definiciones locales del Kanban
- **Acción:** documentar 36 tareas localmente sin sincronización remota.
- **Dependencias:** E0.1, E0.2.
- **Archivos:** Definiciones locales de seguimiento interno.
- **Consigna/alcance:** seguimiento local interno, no entregable funcional.
- **RN/HU:** catálogo E0–E10; HU-TPI-01–06.
- **Criterio de aceptación:** IDs E0.1–E10.3 únicos; ninguna mutación/eliminación de tarjetas del parcial ni llamada de sync ejecutada.
- **Estado:** [COMPLETADA].
- **Evidencia:** 36 IDs únicos y trazados contra la resolución; validación y sintaxis verificadas estáticamente. No se ejecutó el sincronizador ni hubo mutación remota.

### Épica 1 — Backend base y configuración

#### E1.1 — Migrar configuración y dependencias backend
- **Acción:** migrar `requirements.txt` desde las versiones TP9 (`bcrypt==5.0.0`, `PyJWT==2.15.1`, `python-multipart==0.0.34`) a las fijadas por la consigna (`passlib[bcrypt]==1.7.4`, `bcrypt==4.0.1`, `python-jose[cryptography]==3.5.0`, `python-multipart==0.0.20`, `pydantic-settings` 2.x, `fastapi[standard]>=0.115`, `sqlmodel>=0.0.22`, `psycopg2-binary` 2.9), manteniendo dependencias de test operativas, y ampliar `Settings(BaseSettings)` en `app/core/config.py` junto con `foodstore-backend/.env.example`.
- **Dependencias:** E0.2.
- **Archivos:** `foodstore-backend/requirements.txt`, `foodstore-backend/.env.example`, `foodstore-backend/app/core/config.py`.
- **Consigna/alcance:** stack backend (`passlib[bcrypt]==1.7.4`, `bcrypt==4.0.1`, `python-jose[cryptography]==3.5.0`, `pydantic-settings`, `python-multipart==0.0.20`) y variables de sección 3.
- **RN/HU:** HU-TPI-01.
- **Criterio de aceptación:** `Settings(BaseSettings)` lee `DATABASE_URL`, `SECRET_KEY` (`Field(min_length=32)`), `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` y `FRONTEND_ORIGIN` (completando las faltantes en `unidad9_backend/app/core/config.py`); `requirements.txt` y `foodstore-backend/.env.example` aptos para `pip install -r requirements.txt` y `cp .env.example .env` sin `setup.sh`, manteniendo dependencias de test operativas.
- **Estado:** [COMPLETADA].
- **Evidencia:** `foodstore-backend/requirements.txt` fijado e instalado en `.venv` (Python 3.13.5, `pip check` sin conflictos: `fastapi==0.165.0`, `sqlmodel==0.0.50`, `pydantic-settings==2.16.3`, `python-jose==3.5.0`, `passlib==1.7.4`, `bcrypt==4.0.1`, `python-multipart==0.0.20`, `pytest==8.4.2`, `httpx==0.28.1`); `foodstore-backend/.env.example` con las 5 variables normativas copiado a `.env`; `foodstore-backend/app/core/config.py` validado (rechaza `SECRET_KEY < 32` y `FRONTEND_ORIGIN='*'`), `passlib`+`bcrypt` y `python-jose` verificados. `.venv/bin/pytest -q` reporta 9 errores de colección preexistentes (`ModuleNotFoundError` en `app.modules.{categorias,productos}.model`/`schema` y `app.core.seed` retirados en la limpieza previa del catálogo) sin regresiones introducidas por E1.1.

#### E1.2 — Preparar engine, sesiones y aplicación API
- **Acción:** trasladar `app/database.py` de TP9 a `app/core/database.py` (`engine`, `create_all_tables`, `session_factory`) y adaptar `app/main.py` (`create_all_tables()` en `lifespan`) para montar `/api/v1` y CORS dinámico desde `Settings`, permitiendo levantar e inicializar el esquema directamente con `uvicorn app.main:app` sin `setup.sh`.
- **Dependencias:** E1.1.
- **Archivos:** `foodstore-backend/app/core/database.py`, `foodstore-backend/app/core/__init__.py`, `foodstore-backend/app/main.py`, `foodstore-backend/app/modules/categorias/router.py`, `foodstore-backend/app/modules/productos/router.py`, `foodstore-backend/tests/test_core_database_main.py`.
- **Consigna/alcance:** PostgreSQL (`engine`, `create_all_tables`, `session_factory`), `/api/v1`, CORS explícito con `allow_origins=[settings.FRONTEND_ORIGIN]` y `allow_credentials=True` (nunca `"*"`), `/docs`, `/redoc`.
- **RN/HU:** HU-TPI-01–06.
- **Criterio de aceptación:** `app/core/database.py` expone `engine`, `create_all_tables` y `session_factory`; `app/main.py` (`create_all_tables()` en `lifespan`) reemplaza orígenes fijos de TP9 por `[settings.FRONTEND_ORIGIN]`, retira `seed_unidades_medida`/`seed_test_admin` del `lifespan` y monta todos los routers bajo `/api/v1` con `/docs` y `/redoc`, permitiendo que `uvicorn app.main:app` levante e inicialice esquema directamente sin requerir `setup.sh` y pase `pytest` de H1.
- **Estado:** [COMPLETADA].
- **Evidencia:** `app/core/database.py` consume `settings.DATABASE_URL` (normaliza `postgres://`/`postgresql://` y `sqlite:///./...` anclado a `BACKEND_DIR`), mantiene `StaticPool` en memoria y `PRAGMA foreign_keys=ON` + `char_length` en SQLite, y expone `session_factory()` (`expire_on_commit=False`), `create_all_tables()` y alias compatibles reexportados en `app/core/__init__.py`. `app/main.py` define `API_V1_PREFIX = "/api/v1"`, `CORS_ORIGINS = [settings.FRONTEND_ORIGIN]` (`allow_credentials=True`), `lifespan` con `create_all_tables()` sin seeds heredados, `GET /api/v1/health` y monta únicamente `categorias_router` (`/categorias`) y `productos_router` (`/productos`) bajo `/api/v1` con `/docs` y `/redoc`. `./.venv/bin/pytest tests/test_core_database_main.py -v` (6 passed en 0.71s) y arranque real con `./.venv/bin/uvicorn app.main:app` sobre SQLite temporal (`200` en `/api/v1/health`, `/docs`, `/redoc` y cabeceras CORS para `http://localhost:5173`).

#### E1.3 — Implementar seed idempotente TPI
- **Acción:** implementar seed idempotente invocable directamente de forma manual (`python -m app.db.seed`, `CE-04`) sin depender de `setup.sh`, y migrar su integración en `setup.sh`/CI.
- **Dependencias:** E2.2, E4.1, E5.2.
- **Archivos:** `foodstore-backend/app/db/seed.py` (objetivo pendiente); `setup.sh`, `.github/workflows/ci.yml`.
- **Consigna/alcance:** `python -m app.db.seed`, admin/Admin1234!, ≥3 categorías y ≥8 productos con stock.
- **RN/HU:** HU-TPI-01, HU-TPI-04.
- **Criterio de aceptación:** seed repetible y consistente con cinco entidades, invocable directamente de forma manual con `python -m app.db.seed` (`CE-04`) sin depender de `setup.sh`; sustituye el seed heredado tras retirar unidades de medida. La aceptación completa corresponde a H2 con E2.2, E4.1 y E5.2; los datos manuales de H1 no la sustituyen ni el seed bloquea H1.
- **Estado:** [PENDIENTE].
- **Evidencia:** `app/db/seed.py` TPI pendiente de implementación y verificación.

### Épica 2 — Modelo de dominio

#### E2.1 — Migrar categoría y producto al UML
- **Acción:** reemplazar modelo y schemas del catálogo.
- **Dependencias:** E1.2.
- **Archivos:** `foodstore-backend/app/modules/categorias/{models,schemas}.py`, `productos/{models,schemas}.py`.
- **Consigna/alcance:** `Categoria`/`Producto`, categoría única, stock entero, schemas `*Update` parciales (`| None = None`) y campos TPI.
- **RN/HU:** HU-TPI-04.
- **Criterio de aceptación:** modelos y DTOs coinciden con campos/relación UML; H1 integra Categoria–Producto y coordina retirada de unidades/N:N con todos los consumidores y pruebas afectados; E2.2 incorpora después los enlaces a pedidos.
- **Estado:** [COMPLETADA].
- **Evidencia:** implementados `app/modules/categorias/{models,schemas}.py` (`Categoria`, `CategoriaCreate`, `CategoriaUpdate`, `CategoriaRead`), `app/modules/productos/{models,schemas}.py` (`Producto`, `ProductoCreate`, `ProductoUpdate`, `ProductoRead`, `ProductoStockUpdate`, `ProductosPaginados`), reexportaciones en `__init__.py` y registro en `app/core/database.py` (`create_all_tables`). Eliminados 9 archivos obsoletos del parcial en `tests/` y reescritos `tests/{test_models,test_categorias_schema,test_productos_schema}.py`. Verificado DDL (`['categorias', 'productos']`), `pytest -v` (`15 passed in 0.75s`) y `GET /api/v1/health` (`200 OK`).

#### E2.2 — Agregar usuario, pedido y detalle
- **Acción:** completar `Usuario` heredado de TP9 (`created_at`, relación `pedidos`, `UserPublic` unificado de 7 campos y `UserCreate.password` con `max_length=72`) e implementar `Pedido` y `DetallePedido` según el UML TPI.
- **Dependencias:** E2.1.
- **Archivos:** `foodstore-backend/app/modules/usuarios/{models,schemas,__init__}.py`, `foodstore-backend/app/modules/pedidos/{models,schemas,__init__}.py`, `foodstore-backend/app/modules/productos/models.py`, `foodstore-backend/app/core/database.py`, `foodstore-backend/tests/{test_models,test_usuarios_schema,test_pedidos_schema}.py`.
- **Consigna/alcance:** cinco tablas totales; relaciones con nombres UML; snapshots y pedido no editable/borrable.
- **RN/HU:** RN-01, RN-05, HU-TPI-01, HU-TPI-03, HU-TPI-05, HU-TPI-06.
- **Criterio de aceptación:** `Usuario` incorpora `created_at` y relación `Usuario.pedidos`/`Pedido.usuario` y unifica `UserPublic` (7 campos, retirando el esquema dual `UserPublic`/`UserAdminPublic` de TP9); `Pedido` y `DetallePedido` cumplen campos (`forma_pago`, `direccion_entrega`, `notas`, `created_at`, `updated_at`, `nombre_producto`, `subtotal`), defaults, relaciones UML (`Pedido.items`, `Producto.detalles`) y schemas exactos.
- **Estado:** [COMPLETADA].
- **Evidencia:** implementados `app/modules/usuarios/{models,schemas,__init__}.py` (`Usuario`, `UserCreate` con validador UTF-8 <= 72 bytes, `UserPublic` unificado de 7 campos), `app/modules/pedidos/{models,schemas,__init__}.py` (`Pedido`, `DetallePedido`, `EstadoPedido`, `FormaPago`, `ItemPedidoCreate`, `PedidoCreate`, `DetallePedidoRead`, `PedidoRead`, `PedidosPaginados`, `CambioEstado`, `ResumenPedidos`), relación `Producto.detalles` en `app/modules/productos/models.py` y registro de las 5 entidades en `app/core/database.py` (`create_all_tables`). Verificado DDL de 5 tablas `['categorias', 'detalle_pedidos', 'pedidos', 'productos', 'usuarios']` y `./.venv/bin/pytest -v` (`19 passed in 0.84s`, incluyendo `test_models.py`, `test_usuarios_schema.py` y `test_pedidos_schema.py`).

### Épica 3 — Repository y Unit of Work

#### E3.1 — Implementar abstracciones base
- **Acción:** migrar `BaseRepository` (`app/core/repository.py`) y `UnitOfWorkBase` (`app/core/unit_of_work.py`) de TP9 hacia `app/core/base_repository.py` y `app/core/unit_of_work.py` (`UnitOfWork`) con `expire_on_commit=False`.
- **Dependencias:** E1.2.
- **Archivos:** `foodstore-backend/app/core/base_repository.py`, `foodstore-backend/app/core/unit_of_work.py`, `foodstore-backend/app/core/__init__.py` y `foodstore-backend/tests/test_base_repository_y_uow.py`.
- **Consigna/alcance:** `get_by_id`, `get_all`, `add`, `delete`; `__enter__` con `Session(engine, expire_on_commit=False)`, `__exit__` con commit/rollback/close.
- **RN/HU:** HU-TPI-03–06.
- **Criterio de aceptación:** `BaseRepository[T]` en `base_repository.py` y `UnitOfWork` sobre fábrica de sesiones, sin esperar el modelo completo de pedidos; `__enter__` abre `Session(engine, expire_on_commit=False)` (corrigiendo `Session(database.engine)` de TP9 para serializar `model_validate` con relaciones dentro del `with`) y `__exit__` hace commit/close o rollback/close según excepción.
- **Estado:** [COMPLETADA].
- **Evidencia:** implementados `app/core/base_repository.py` (`BaseRepository[T]`, `ModelType`, `get_by_id`, `get_all` con `skip`/`offset`/`limit`, `add`, `delete`, `create`, `update` sin `commit`), `app/core/unit_of_work.py` (`UnitOfWork` y alias `UnitOfWorkBase`, `_init_repositories`, `expire_on_commit=False`, `__enter__`/`__exit__` con `commit`/`rollback`/`close` y métodos manuales con `RuntimeError` sin sesión) y reexportaciones en `app/core/__init__.py`. Verificados `tests/test_base_repository_y_uow.py` (10 pruebas unitarias con `SessionDouble` y en SQLite en memoria incluyendo `ProductoRead.model_validate` con relación `categoria` y acceso post-commit), `./.venv/bin/pytest -v` (`29 passed in 0.91s`) y comprobación de importaciones desde `app.core`.

#### E3.2 — Añadir UoW/repositorios de categorías y productos
- **Acción:** conectar repositorios a la misma sesión de trabajo.
- **Dependencias:** E2.1, E3.1.
- **Archivos:** `foodstore-backend/app/modules/categorias/{repository,unit_of_work,__init__}.py`, `foodstore-backend/app/modules/productos/{repository,unit_of_work,__init__}.py`, `foodstore-backend/tests/test_categorias_productos_repo_uow.py`.
- **Consigna/alcance:** métodos `get_by_nombre` (`categorias`) y `search` (`productos`); retirar commits de Services/Routers al migrar operaciones en E5.1/E5.2.
- **RN/HU:** HU-TPI-04.
- **Criterio de aceptación:** servicios usan `with self.uow as uow:` y devuelven schemas con `model_validate` dentro del bloque; Router no abre UoW ni llama `session.commit()`. Integración H1 del catálogo con contrato coordinado.
- **Estado:** [COMPLETADA].
- **Evidencia:** implementados `CategoriaRepository` (`get_by_nombre` incluyendo inactivas, `list_activas`/`get_all_activas`, `get_activa_by_id`), `CategoriaUnitOfWork`, `ProductoRepository` (`get_by_id` y `get_activo_by_id` con `selectinload(Producto.categoria)`, `search` case-insensitive con filtros `search`/`nombre`, `categoria_id`, `disponible`, paginación `skip`/`limit` y `total` exacto), `ProductoUnitOfWork` (sesión compartida entre `productos` y `categorias`) y sus reexportaciones en `__init__.py` (sin modificar `service.py` ni `router.py`, que se migran en E5.1/E5.2). Verificados `./.venv/bin/pytest tests/test_categorias_productos_repo_uow.py -v` (`4 passed in 0.70s`), `./.venv/bin/pytest -v` (`33 passed in 0.85s`) e importación de símbolos junto con `app.main.app`.

#### E3.3 — Añadir repositorio/UoW de pedidos
- **Acción:** coordinar pedidos y productos dentro de unidad de trabajo.
- **Dependencias:** E2.2, E3.1, E3.2.
- **Archivos:** `foodstore-backend/app/modules/pedidos/{repository,unit_of_work,__init__}.py`, `foodstore-backend/tests/test_pedidos_repo_uow.py`.
- **Consigna/alcance:** métodos `list_by_usuario`, `count_by_estado`, `list_all`/`list_paginado`, `add_detalle`, `count_estado`, `count_pedidos_hoy`, `sum_ingresos_entregados` y `get_by_id`/`get_by_id_with_items` con `selectinload(Pedido.items)`; `PedidoUnitOfWork` con sesión compartida entre pedidos y productos.
- **RN/HU:** RN-01–05, HU-TPI-03, HU-TPI-05.
- **Criterio de aceptación:** integra con las entidades y repositorios reales de pedidos; operaciones de pedido y stock comparten transacción UoW.
- **Estado:** [COMPLETADA].
- **Evidencia:** implementados `PedidoRepository` (extiende `BaseRepository[Pedido]` con `get_by_id` y `get_by_id_with_items` usando `selectinload(Pedido.items)`, `add_detalle`, `list_by_usuario`, `list_all` y alias `list_paginado` ordenados por `created_at desc, id desc` con filtro opcional por `estado`, `count_by_estado` garantizando las 4 claves, `count_estado`, `count_pedidos_hoy` y `sum_ingresos_entregados` con `coalesce`, sin llamadas a `commit()` ni reglas de negocio), `PedidoUnitOfWork` (sesión compartida con `expire_on_commit=False` entre `pedidos: PedidoRepository` y `productos: ProductoRepository`) y reexportaciones en `app/modules/pedidos/__init__.py` (sin crear `service.py` ni `router.py`, reservados para E6.1–E6.4). Verificados `./.venv/bin/pytest tests/test_pedidos_repo_uow.py -v` (`5 passed in 0.78s`), `./.venv/bin/pytest -v` (`38 passed in 1.00s`), importación de `PedidoRepository`, `PedidoUnitOfWork` y `app.main.app`, y ausencia de llamadas reales a `.commit(` en repositorios.

### Épica 4 — Seguridad, autenticación y usuarios

#### E4.1 — Implementar criptografía y JWT
- **Acción:** extraer el hash/verificación y creación/decodificación JWT de `unidad9_backend/app/modules/usuarios/service.py` (`bcrypt==5.0.0` + `PyJWT==2.15.1`) hacia `app/core/security.py` migrando a `passlib[bcrypt]==1.7.4`, `bcrypt==4.0.1` y `python-jose[cryptography]==3.5.0`.
- **Dependencias:** E2.2.
- **Archivos:** `app/core/security.py` y `app/modules/usuarios/schemas.py` (`UserCreate.password` con `max_length=72`).
- **Consigna/alcance:** claims `sub`, `role`, `type="access"`, `exp`; límite de 72 bytes UTF-8 de bcrypt.
- **RN/HU:** HU-TPI-01.
- **Criterio de aceptación:** contraseñas almacenadas con `passlib` (`bcrypt==4.0.1`) y `UserCreate.password` acotado con `Field(min_length=8, max_length=72)`; JWT incluye `sub`, `role`, `type="access"` y `exp` usando `Settings` (`SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`); token nunca expuesto en cuerpo de login y `hashed_password` nunca serializado.
- **Estado:** [PENDIENTE].
- **Evidencia:** `unidad9_backend/app/modules/usuarios/service.py` prueba bcrypt (`bcrypt==5.0.0`) y JWT (`PyJWT`, solo `sub`/`iat`/`exp`), sin `app/core/security.py` ni claims `role`/`type="access"`.

#### E4.2 — Implementar endpoints de autenticación
- **Acción:** separar `app/modules/auth/{router,service,schemas}.py` desde el router/servicio unificado de `usuarios` en TP9, ajustando el cuerpo de respuesta de `/auth/token` y el esquema `UserPublic`.
- **Dependencias:** E4.1.
- **Archivos:** `app/modules/auth/{router,service,schemas}.py` (objetivo pendiente).
- **Consigna/alcance:** cookie `access_token` emitida y borrada con `httponly=True` y `samesite="lax"` (30 min por defecto).
- **RN/HU:** HU-TPI-01.
- **Criterio de aceptación:** `POST /api/v1/auth/register` responde 201 `UserPublic` (7 campos) o 409 (`UsuarioDuplicado`); `POST /api/v1/auth/token` responde `200 {"message": "Login exitoso"}` (en lugar de `UserPublic` en TP9), 401 credenciales inválidas y 400 `"Cuenta de usuario desactivada"`; `set_cookie` (`/auth/token`) y `delete_cookie` (`/auth/logout`) con `httponly=True` y `samesite="lax"`; `GET /api/v1/auth/me` devuelve `UserPublic`.
- **Estado:** [PENDIENTE].
- **Evidencia:** `unidad9_backend/app/modules/usuarios/router.py` prueba `/auth/{register,token,logout,me}` con tests (`test_auth_router.py`), pero devuelve `UserPublic` en `/token` y convive con rutas admin en un único módulo.

#### E4.3 — Implementar dependencias de sesión y rol
- **Acción:** migrar `dependencies.py` de `unidad9_backend/app/modules/usuarios/` a `app/core/deps.py`, sustituyendo `Cookie()` directo por `OAuth2PasswordBearerWithCookie` y devolviendo `UserPublic` en `require_role`.
- **Dependencias:** E4.2.
- **Archivos:** `app/core/deps.py` (objetivo pendiente).
- **Consigna/alcance:** extracción exclusiva desde cookie `access_token` (rechaza `Authorization: Bearer`); consulta autoritativa en PostgreSQL en `get_current_user` en cada petición y patrón factory en `require_role(allowed_roles)` devolviendo `UserPublic`; backend hace cumplir permisos.
- **RN/HU:** HU-TPI-01, HU-TPI-04–06.
- **Criterio de aceptación:** `OAuth2PasswordBearerWithCookie` rechaza `Authorization: Bearer`; `get_current_user` valida `type == "access"` y consulta PostgreSQL en cada petición (401 si sesión inválida/ausente/expirada o `type != "access"`), `get_current_active_user` retorna 400 `"Cuenta de usuario desactivada"`, y `require_role(allowed_roles)` como factory devuelve `UserPublic` o 403 si rol no autorizado.
- **Estado:** [PENDIENTE].
- **Evidencia:** `unidad9_backend/app/modules/usuarios/dependencies.py` implementa consulta en DB, 400 desactivada y `require_role` con tests (`test_role_dependencies.py`), pero usa `Cookie()` directo, no valida `type == "access"` y retorna `Usuario` en lugar de `UserPublic`.

#### E4.4 — Gestionar usuarios desde admin
- **Acción:** refactorizar los endpoints administrativos de `unidad9_backend/app/modules/usuarios/router.py` a `/api/v1/admin/usuarios` bajo `app/modules/usuarios/`, con `UnitOfWork` (`expire_on_commit=False`), listado completo y bloqueo de auto-desactivación.
- **Dependencias:** E4.3.
- **Archivos:** `app/modules/usuarios/{models,schemas,repository,unit_of_work,service,router}.py` (objetivo pendiente).
- **Consigna/alcance:** métodos `get_by_username`, `get_by_email` en repositorio; operaciones solo admin.
- **RN/HU:** HU-TPI-06.
- **Criterio de aceptación:** rutas en `/api/v1/admin/usuarios`, `/{id}/activar` y `/{id}/desactivar` (fuera de `/api/v1/auth`); `GET /api/v1/admin/usuarios` devuelve `list[UserPublic]` (7 campos) sin ocultar usuarios desactivados por defecto; activar/desactivar son idempotentes (200); inexistente 404 (`UsuarioNoEncontrado`); auto-desactivación del admin autenticado responde 400.
- **Estado:** [PENDIENTE].
- **Evidencia:** `unidad9_backend/app/modules/usuarios/` expone rutas bajo `/api/v1/auth/admin/usuarios`, oculta desactivados por defecto (`incluir_desactivados=False`), usa `UserAdminPublic` (6 campos) y no bloquea auto-desactivación (`test_admin_users.py`).

### Épica 5 — API de catálogo

#### E5.1 — Migrar CRUD de categorías
- **Acción:** migrar operaciones a UoW y excepciones de dominio (`CategoriaNoEncontrada`, `NombreDuplicado`).
- **Dependencias:** E3.2, E4.3.
- **Archivos:** `app/modules/categorias/{models,schemas,repository,unit_of_work,service,router}.py`.
- **Consigna/alcance:** lecturas activas públicas, escrituras admin, `get_by_nombre`, `CategoriaUpdate` parcial (`| None = None` con `model_dump(exclude_unset=True)`), baja lógica.
- **RN/HU:** HU-TPI-04.
- **Criterio de aceptación:** lecturas públicas de categorías activas disponibles desde H1; cierre CRUD, nombre reservado tras baja (`NombreDuplicado` 409), categorías inactivas 404 (`CategoriaNoEncontrada`) y DELETE 204 en H2. Mientras auth esté pendiente, no se habilitan escrituras sin control admin.
- **Estado:** [PENDIENTE].
- **Evidencia:** CRUD heredado no demuestra estas reglas.

#### E5.2 — Migrar CRUD y consultas de productos
- **Acción:** adaptar DTOs, categoría única, filtros (`search`) y paginación.
- **Dependencias:** E5.1.
- **Archivos:** `app/modules/productos/{models,schemas,repository,unit_of_work,service,router}.py`, frontend consumidores y pruebas afectadas.
- **Consigna/alcance:** retirar clasificación N:N y contratos antiguos; `ProductoUpdate` parcial (`| None = None` con `model_dump(exclude_unset=True)`).
- **RN/HU:** HU-TPI-02, HU-TPI-04.
- **Criterio de aceptación:** lecturas públicas de catálogo disponibles en H1; cierre en H2 de `categoria_id`, `stock: int`, búsqueda/filtros (`search` por nombre/categoría/disponible) y respuesta `{total,items}`; PUT parcial; límite máximo 100; `ProductoNoEncontrado`/`CategoriaNoEncontrada` 404. Mientras auth esté pendiente, no se habilitan escrituras sin control admin.
- **Estado:** [PENDIENTE].
- **Evidencia:** catálogo heredado y límite/DTO anteriores no prueban el objetivo.

#### E5.3 — Implementar stock, disponibilidad y baja lógica
- **Acción:** endpoints de PATCH y eliminación lógica.
- **Dependencias:** E5.2.
- **Archivos:** `productos/router.py`, `service.py`, schemas.
- **Consigna/alcance:** admin modifica; público consulta activos.
- **RN/HU:** HU-TPI-04.
- **Criterio de aceptación:** stock no negativo, cambio de disponibilidad y DELETE 204 lógico, con permisos.
- **Estado:** [PENDIENTE].
- **Evidencia:** comportamiento heredado requiere migración.

### Épica 6 — Pedidos y reglas transaccionales

#### E6.1 — Crear pedido transaccional
- **Acción:** implementar POST con validación, snapshot, total y descuento usando excepciones de dominio (`ProductoNoEncontrado`, `ProductoNoDisponible`, `ProductoRepetido`, `StockInsuficiente`).
- **Dependencias:** E3.3, E5.3.
- **Archivos:** `app/modules/pedidos/{models,schemas,repository,unit_of_work,service,router}.py` (objetivo pendiente).
- **Consigna/alcance:** RN-01, RN-05, RN-06.
- **RN/HU:** HU-TPI-03.
- **Criterio de aceptación:** al menos un ítem, sin repetidos (`ProductoRepetido` 400), producto vendible (`ProductoNoEncontrado` 404 / `ProductoNoDisponible` 400) y stock suficiente (`StockInsuficiente` 400); snapshot/total correctos; prueba del caso dos líneas, segunda sin stock demuestra rollback total sin pedido ni descuento de primera.
- **Estado:** [PENDIENTE].
- **Evidencia:** pedidos y transacciones TPI no se atribuyen a la base heredada.

#### E6.2 — Validar transiciones y cancelación
- **Acción:** implementar máquina de 4 estados y restitución idempotente por transición terminal (`TransicionInvalida` 400).
- **Dependencias:** E6.1.
- **Archivos:** `app/modules/pedidos/service.py` y `unit_of_work.py` objetivo.
- **Consigna/alcance:** RN-02 y RN-03.
- **RN/HU:** HU-TPI-03, HU-TPI-05.
- **Criterio de aceptación:** transición inválida 400 (`TransicionInvalida`); terminal inmutable; stock restituido una sola vez en transacción.
- **Estado:** [PENDIENTE].
- **Evidencia:** sin implementación TPI acreditada.

#### E6.3 — Implementar consulta y permisos de pedidos
- **Acción:** lista, detalle y cancelación del propietario/admin (`PedidoNoEncontrado` 404, `PedidoAjeno` 403).
- **Dependencias:** E6.2.
- **Archivos:** `app/modules/pedidos/{router,service,schemas}.py` (objetivo pendiente).
- **Consigna/alcance:** RN-04; paginación normalizada.
- **RN/HU:** HU-TPI-03.
- **Criterio de aceptación:** ajeno 403 (`PedidoAjeno`), inexistente 404 (`PedidoNoEncontrado`); cliente cancela solo propio `PENDIENTE`; respuesta paginada `{total,items}`.
- **Estado:** [PENDIENTE].
- **Evidencia:** no existe evidencia heredada de pedidos.

#### E6.4 — Implementar resumen administrativo
- **Acción:** endpoint de resumen de negocio.
- **Dependencias:** E6.3.
- **Archivos:** `pedidos/router.py`, service, schemas (objetivo pendiente).
- **Consigna/alcance:** `ResumenPedidos`; declarar `/pedidos/resumen` antes de `/{id}`.
- **RN/HU:** HU-TPI-05.
- **Criterio de aceptación:** conteos por estado, pedidos de hoy e ingresos por suma de `total` de entregados.
- **Estado:** [PENDIENTE].
- **Evidencia:** resumen TPI no implementado/acreditado.

### Épica 7 — Infraestructura de frontend y estado

#### E7.1 — Migrar stack y organización frontend
- **Acción:** migrar la estructura plana de `unidad9_frontend` (`src/{api,components,pages,services,store,types}/`) hacia `src/shared/{api,ui,components,layout}`, `src/features/{auth,categorias,productos,usuarios,pedidos}`, `src/store/` y `src/routes/`, configurando alias `@/`, `timeout: 15_000`, `handleApiError.ts`, `queryClient.ts`, `VITE_API_URL` con `/api/v1` y versiones objetivo (`TypeScript >=5.9`, `Vite >=7`).
- **Dependencias:** E0.1.
- **Archivos:** `foodstore-frontend/package.json`, `foodstore-frontend/.env.example`, `foodstore-frontend/vite.config.ts`, `foodstore-frontend/tsconfig.app.json`, `src/main.tsx`, `src/shared/api/{axiosInstance,handleApiError,queryClient}.ts`, `src/routes/AppRouter.tsx` (objetivo pendiente).
- **Consigna/alcance:** React 19/TS estricto (`strict: true`, sin `any`); URL API `VITE_API_URL` con `/api/v1`.
- **RN/HU:** HU-TPI-01–06.
- **Criterio de aceptación:** infraestructura común puede avanzar desde el contrato documental E0.1 y conectarse a lecturas H1; APIs de pedidos no son prerrequisito. `package.json` y `foodstore-frontend/.env.example` (`VITE_API_URL=http://localhost:8000/api/v1`) listos desde H1 para `cp .env.example .env`, `pnpm install`, `pnpm build` y `pnpm dev` sin `setup.sh`, manteniendo `Vitest` operativo. Configuración dual de `@/`: `vite.config.ts` (`resolve.alias` con `import.meta.dirname` y `@types/node` en `devDependencies`) y `tsconfig.app.json` (`paths: { "@/*": ["./src/*"] }`); reglas de barrel exports `index.ts` en las 5 features (exports nombrados, sin `export *`, sin imports externos a subcarpetas privadas `RA-01` y sin auto-importar el propio barrel). `axiosInstance.ts` único en `src/shared/api/` con `withCredentials: true`, `timeout: 15_000`, `baseURL = VITE_API_URL` (`/api/v1`), `setUnauthorizedHandler` (ampliado a `400` desactivada), y `handleApiError.ts` preservando `error.cause` (retirando `src/services/api.ts`); `queryClient.ts` extraído de `main.tsx`; probar cada consumidor al integrarlo.
- **Estado:** [PENDIENTE].
- **Evidencia:** `unidad9_frontend` ya resuelve `axiosInstance.ts` con `withCredentials`, `setUnauthorizedHandler` (401) y `error.cause` (`axiosInstance.test.ts`), pero mantiene estructura plana sin `@/`, sin `timeout: 15_000`, con `VITE_API_URL` sin `/api/v1` y con `src/services/api.ts` heredado.

#### E7.2 — Implementar authStore y rutas protegidas
- **Acción:** migrar `src/store/authStore.ts` (que en TP9 ya implementa `persist`+`partialize`, `checkSession` y `logout` `try/finally`) al esquema TPI (`usuario`, `cargando`, selectores atómicos/`useShallow`), ampliar `setUnauthorizedHandler` a `400` `"Cuenta de usuario desactivada"` y migrar `ProtectedRoute` de `children` a `<Outlet />` en `src/routes/`.
- **Dependencias:** E7.1, E4.3.
- **Archivos:** `src/store/authStore.ts`, `src/routes/{AppRouter,ProtectedRoute}.tsx`, `src/App.tsx` (objetivo pendiente).
- **Consigna/alcance:** Zustand 5 con selectores atómicos, `useShallow` y `persist`/`partialize` guardando solo `usuario`.
- **RN/HU:** HU-TPI-01.
- **Criterio de aceptación:** sesión/rutas protegidas dependen de auth y roles, no del ABM de usuarios; limpiar `usuario` vía `setUnauthorizedHandler` ante 401 fuera de `/auth/token` y `/auth/me` y 400 `"Cuenta de usuario desactivada"` (`403` nunca dispara `setUnauthorizedHandler` ni limpia sesión); `checkSession()` único en `useEffect` al montar `App.tsx`; `logout()` con `try/finally`; JWT nunca persistido. `ProtectedRoute` con `<Outlet />` (en lugar de `children` en TP9) respeta el orden (`cargando` -> `!usuario` con `state={{ from: location }}` -> `allowedRoles` redirige a `/unauthorized`); `AppRouter` agrupa rutas públicas, con sesión y admin (`allowedRoles=['admin']`).
- **Estado:** [PENDIENTE].
- **Evidencia:** `unidad9_frontend` ya prueba `authStore.ts` (`persist`+`partialize` de `user` en `sessionStorage`, `login`, `checkSession`, `logout` `try/finally`) y `ProtectedRoute` con `children` (`authStore.test.ts`, `AppSession.test.tsx`, `ProtectedRoute.test.tsx`); falta migrar a `Outlet`, campos TPI y handler `400`.

#### E7.3 — Implementar cartStore y piezas compartidas
- **Acción:** carrito persistido y estados/UI comunes.
- **Dependencias:** E7.1.
- **Archivos:** `src/store/cartStore.ts`, `src/shared/{ui,components,layout}/` objetivo pendiente.
- **Consigna/alcance:** primitivas de carrito (`Zustand 5` + `persist`, selectores atómicos/`useShallow`) y estados accesibles.
- **RN/HU:** HU-TPI-02, HU-TPI-03.
- **Criterio de aceptación:** operaciones y total de carrito observables; componentes compartidos reutilizables con teclado, foco visible y estados distintos; estado efímero local sin duplicar datos remotos; cierre de carrito en H2. Aplicar 3.6.
- **Estado:** [PENDIENTE].
- **Evidencia:** carrito TPI no acreditado.

### Épica 8 — Frontend cliente

#### E8.1 — Crear login, registro y acceso no autorizado
- **Acción:** migrar `LoginPage`, `RegisterPage` (ambas ya implementadas con `@tanstack/react-form` en TP9) y `UnauthorizedPage` hacia `src/features/auth/`, desacoplando la llamada HTTP de registro en `features/auth/api/` + hook Query y ajustando las rutas destino (`location.state?.from?.pathname ?? '/'` y `'/'`).
- **Dependencias:** E7.2.
- **Archivos:** `src/features/auth/{pages,api,hooks,types,index.ts}` (`LoginPage.tsx`, `RegisterPage.tsx`, `UnauthorizedPage.tsx`) (objetivo pendiente).
- **Consigna/alcance:** TanStack Form, sesión confirmada por backend.
- **RN/HU:** HU-TPI-01.
- **Criterio de aceptación:** login/registro con `@tanstack/react-form` enviables por teclado, errores asociados al campo/operación, fallo conserva entradas y no confirma sesión inexistente; `RegisterPage` consume `features/auth/api/` + TanStack Query (sin `axiosInstance` directo en `pages/`); `LoginPage` tras login exitoso redirige a `location.state?.from?.pathname ?? '/'` con `{ replace: true }` (en lugar de `'/categories'`); `UnauthorizedPage` enlaza a `'/'` (en lugar de `'/categories'`); logout limpia store y redirige. Aplicar 3.6.
- **Estado:** [PENDIENTE].
- **Evidencia:** `unidad9_frontend/src/pages/{LoginPage,RegisterPage,UnauthorizedPage}.tsx` ya resuelven `@tanstack/react-form` y validaciones (`RegisterPage.test.tsx`), pero usan rutas `/categories`, llamada directa a `axiosInstance` en `RegisterPage` y carpeta plana `src/pages/`.

#### E8.2 — Adaptar catálogo público
- **Acción:** consulta de catálogo, búsqueda, filtro y compra al carrito.
- **Dependencias:** E7.3, E5.2.
- **Archivos:** `features/productos/` objetivo pendiente; componentes actuales reutilizables con adaptación.
- **Consigna/alcance:** paginación de servidor, skeleton y vacío.
- **RN/HU:** HU-TPI-02.
- **Criterio de aceptación:** H1 puede mostrar la primera lectura pública; cierre en H2 de búsqueda/filtro/paginación remota y agregar al carrito accesibles; refetch fallido conserva resultados útiles e informa fallo, sin convertirlo en vacío. Aplicar 3.6.
- **Estado:** [PENDIENTE].
- **Evidencia:** el catálogo actual no contiene contrato/carrito TPI acreditado.

#### E8.3 — Crear carrito y checkout
- **Acción:** resumen, formulario y envío de pedido.
- **Dependencias:** E8.1, E8.2, E6.3.
- **Archivos:** `features/pedidos/` objetivo pendiente.
- **Consigna/alcance:** dirección, pago, notas; TanStack Form.
- **RN/HU:** RN-01, RN-05, RN-06; HU-TPI-03.
- **Criterio de aceptación:** tras disponer de APIs de creación, listado, detalle y cancelación de pedidos, el POST verifica validación textual de campos y estado de envío; si falla conserva formulario/carrito y no redirige; vacía carrito y navega solo tras éxito. Aplicar 3.6.
- **Estado:** [PENDIENTE].
- **Evidencia:** checkout TPI no acreditado.

#### E8.4 — Crear mis pedidos y detalle
- **Acción:** lista/detalle de pedidos propios y cancelación.
- **Dependencias:** E8.3, E6.3.
- **Archivos:** `features/pedidos/pages/` objetivo pendiente.
- **Consigna/alcance:** cancelación visible solo en `PENDIENTE`.
- **RN/HU:** RN-03–05; HU-TPI-03.
- **Criterio de aceptación:** carga/vacío/error distinguibles; consulta/listado/detalle/cancelación API disponibles; cancelación fallida conserva datos y no cambia estado como éxito; éxito invalida consultas afectadas. Aplicar 3.6.
- **Estado:** [PENDIENTE].
- **Evidencia:** flujo TPI no acreditado.

### Épica 9 — Frontend administración

#### E9.1 — Crear resumen admin
- **Acción:** tarjetas de indicadores.
- **Dependencias:** E7.2, E6.4.
- **Archivos:** `features/pedidos/pages/AdminResumenPage` (objetivo pendiente).
- **Consigna/alcance:** TanStack Query y protección admin.
- **RN/HU:** HU-TPI-05.
- **Criterio de aceptación:** indicadores protegidos por rol con carga/error/datos diferenciados; refetch fallido conserva valores previos identificados como tales. Aplicar 3.6.
- **Estado:** [PENDIENTE].
- **Evidencia:** pantalla no acreditada.

#### E9.2 — Crear ABM de categorías/productos
- **Acción:** tablas/formularios, stock y disponibilidad.
- **Dependencias:** E7.2, E7.3, E5.3.
- **Archivos:** `features/categorias/`, `features/productos/` objetivo pendiente.
- **Consigna/alcance:** Table/Form; paginación local con API `limit=100`.
- **RN/HU:** HU-TPI-04.
- **Criterio de aceptación:** tablas semánticas y controles por teclado; fallos de guardado conservan edición/formulario y muestran error; éxito invalida datos; refetch fallido no borra contenido anterior. Aplicar 3.6.
- **Estado:** [PENDIENTE].
- **Evidencia:** UI actual es de catálogo heredado.

#### E9.3 — Crear gestión admin de pedidos
- **Acción:** tabla, filtro y acciones de transición/cancelación.
- **Dependencias:** E7.2, E6.4.
- **Archivos:** `features/pedidos/pages/AdminPedidosPage` (objetivo pendiente).
- **Consigna/alcance:** botones acordes a máquina de estados.
- **RN/HU:** RN-02–05; HU-TPI-05.
- **Criterio de aceptación:** transición rechazada conserva pedido/estado confirmado y muestra error; solo éxito confirma transición e invalida lista/detalle/resumen/stock. Aplicar 3.6.
- **Estado:** [PENDIENTE].
- **Evidencia:** no se acredita UI de pedidos.

#### E9.4 — Crear gestión admin de usuarios
- **Acción:** migrar `AdminUsersPage` de TP9 hacia `src/features/usuarios/` (`AdminUsuariosPage`, `useUsuarios`, `api/`, `types/`, `index.ts`) usando TanStack Query y TanStack Table (`limit=100`), consumiendo `/api/v1/admin/usuarios` y ocultando `"Desactivar"` en la fila propia.
- **Dependencias:** E7.2, E4.4.
- **Archivos:** `src/features/usuarios/` (`AdminUsuariosPage`, `useUsuarios`, `api/`, `types/`, `index.ts`) (objetivo pendiente).
- **Consigna/alcance:** ocultar el botón "Desactivar" en la fila del usuario de la sesión.
- **RN/HU:** HU-TPI-06.
- **Criterio de aceptación:** tabla semántica con TanStack Table y consultas/mutaciones en TanStack Query (reemplazando `useState`/`useEffect` y `axiosInstance` directo de TP9); consume `/api/v1/admin/usuarios` (sin parámetro `incluir_desactivados` ni prefijo `/auth`) con `UserPublic` (7 campos); activar/desactivar fallido conserva usuario/estado confirmado y muestra error; solo éxito confirma cambio e invalida datos; el botón "Desactivar" se oculta en la fila del usuario de la sesión. Aplicar 3.6.
- **Estado:** [PENDIENTE].
- **Evidencia:** `unidad9_frontend/src/pages/AdminUsersPage.tsx` (`AdminUsersPage.test.tsx`) gestiona activar/desactivar vía `useState`/`useEffect` sobre `/api/v1/auth/admin/usuarios` y muestra `"Desactivar"` incluso en la fila propia.

### Épica 10 — Verificación y entrega

#### E10.1 — Verificación integral final del flujo TPI
- **Acción:** verificar el sistema integrado en PostgreSQL/navegador levantando el proyecto manualmente según `README.md` sin depender de `setup.sh`, con `pytest`/`Vitest` en verde como respaldo previo, y actualizar evidencia por criterio.
- **Dependencias:** E1.3, E8.4, E9.1, E9.2, E9.3, E9.4.
- **Archivos:** aplicación y matriz de evidencia.
- **Consigna/alcance:** registro, compra, administración, cancelación y restitución.
- **RN/HU:** RN-01–06; HU-TPI-01–06.
- **Criterio de aceptación:** verificación integral final ejecutada manualmente según `README.md` sin depender de `setup.sh`, posterior a comprobaciones por incremento y con `pytest`/`Vitest` en verde como respaldo previo; evidencia reproducible actual, sin reutilizar resultados del parcial.
- **Estado:** [PENDIENTE].
- **Evidencia:** no realizada por esta actualización documental.

#### E10.2 — Alinear automatización al sistema TPI
- **Acción:** adaptar `setup.sh`/CI y consolidar la ejecución final de las suites de testing continuo (`pytest` + `TestClient` con `StaticPool` en backend; `Vitest`/Testing Library en frontend) sobre los módulos Food Store tras `E10.1`; las carpetas de tests no se eliminan ni excluyen en esta etapa.
- **Dependencias:** E10.1.
- **Archivos:** `setup.sh`, `.github/workflows/ci.yml`, `tests/` (red de verificación interna).
- **Consigna/alcance:** retirar comprobaciones obsoletas de unidades/N:N y fases del parcial; actualizar referencias de tests a `auth`, `usuarios`, `categorias`, `productos` y `pedidos` manteniendo operativas las suites hasta completar esta etapa.
- **RN/HU:** cobertura proporcional de RN-01–06 y HU-TPI-01–06.
- **Criterio de aceptación:** ejecución final de `pytest`/`Vitest` en verde consolidada junto con `setup.sh` y CI tras `E10.1` sin gates heredados incompatibles; las carpetas de tests no se eliminan ni excluyen en esta etapa.
- **Estado:** [PENDIENTE].
- **Evidencia:** automatización actual es heredada.

#### E10.3 — Preparar entrega normativa
- **Acción:** completar README raíz y materiales de entrega, realizando recién en esta etapa la exclusión/limpieza final de la suite de pruebas descartable al generar el `.zip` (`CE-01`).
- **Dependencias:** E10.2.
- **Archivos:** `README.md`, `presentation/mindmap_presentacion.mmd` (apoyo local opcional del guion), ZIP de entrega, URL repositorio y video (pendientes).
- **Consigna/alcance:** repo público con URL real; ZIP sin `node_modules`, `venv`, `.env` ni suite de pruebas descartable (`foodstore-backend/tests/`, `foodstore-frontend/src/__tests__/`, `.pytest_cache/`, `coverage/`) (`CE-01`), excluida únicamente en `E10.3` y no antes; video público 10–15 min, cámara al inicio, registro, compra, administración y cancelación mostrando restitución.
- **RN/HU:** RN-01–06; HU-TPI-01–06.
- **Criterio de aceptación:** guía ejecutable en máquina limpia sin `setup.sh`; ZIP limpio excluyendo dependencias, `.env` y la suite de pruebas descartable (`foodstore-backend/tests/`, `foodstore-frontend/src/__tests__/`, `.pytest_cache/`, `coverage/`), limpieza realizada únicamente en `E10.3` y no antes; el mindmap es apoyo local opcional, no dependencia de ejecución, entregable normativo ni evidencia de grabación; siete entregables trazados en sección 5.
- **Estado:** [PENDIENTE].
- **Evidencia:** publicación y video pendientes; no se inventan URLs.

## 5. Trazabilidad y verificación

La rúbrica asigna 100 puntos al código entregado; las ponderaciones siguientes son las de la consigna, no puntaje obtenido. Pruebas automatizadas no son requisito académico explícito. La columna evidencia distingue infraestructura heredada de cumplimiento TPI; la comprobación es futura.

### 5.1 Criterios de evaluación

| # / criterio | Pts | Tareas | Evidencia existente (base) | Brecha TPI | Comprobación futura | Estado |
|---|---:|---|---|---|---|---|
| 1. Backend: estructura y configuración | 10 | E1.1–E1.3, E10.2 | E1.1 y E1.2 completadas: `requirements.txt`, `.env.example`, `app/core/config.py`, `app/core/database.py` (`engine`, `create_all_tables`, `session_factory` con `expire_on_commit=False`), `app/main.py` (`/api/v1`, `lifespan`, CORS `[settings.FRONTEND_ORIGIN]` con `allow_credentials=True`, `/api/v1/health`, `/docs`, `/redoc`) y `tests/test_core_database_main.py` (6 passed) + arranque `uvicorn` sobre SQLite verificados. | Implementar `app/db/seed.py` (E1.3) y consolidar suite/CI en E10.2; verificar sobre PostgreSQL limpio sin `setup.sh`. | Inspección de capas, `.env.example`, ejecución manual de seed y API sin `setup.sh`. | Pendiente |
| 2. Modelo de datos | 10 | E2.1–E2.2 | E2.1 y E2.2 completadas: 5 entidades UML (`Categoria`, `Producto`, `Usuario`, `Pedido`, `DetallePedido`), relaciones bidireccionales y schemas TPI (`UserPublic` unificado de 7 campos, `UserCreate` <= 72 bytes UTF-8, schemas de `pedidos`), registrados en `create_all_tables()`. Verificado DDL `['categorias', 'detalle_pedidos', 'pedidos', 'productos', 'usuarios']` y `pytest -v` (`19 passed in 0.84s`). | Sin brecha de modelos/schemas; resta contrastar respuestas HTTP de endpoints y DDL en PostgreSQL limpio (E6.1–E6.4, E10.1). | Contrastar modelos/DDL y respuestas con UML en PostgreSQL. | Parcial (modelos/SQLite verificados) |
| 3. Unit of Work y Repository | 10 | E3.1–E3.3 | E3.1, E3.2 y E3.3 completadas: `app/core/base_repository.py` (`BaseRepository[T]`), `app/core/unit_of_work.py` (`UnitOfWork` con `expire_on_commit=False`), `app/modules/categorias/{repository,unit_of_work}.py` (`CategoriaRepository`, `CategoriaUnitOfWork`), `app/modules/productos/{repository,unit_of_work}.py` (`ProductoRepository`, `ProductoUnitOfWork` con sesión compartida y `selectinload(Producto.categoria)`), `app/modules/pedidos/{repository,unit_of_work}.py` (`PedidoRepository`, `PedidoUnitOfWork` con sesión compartida entre pedidos y productos y `selectinload(Pedido.items)`), `tests/test_base_repository_y_uow.py`, `tests/test_categorias_productos_repo_uow.py` y `tests/test_pedidos_repo_uow.py` (`pytest -v`: `38 passed in 1.00s`). | Agregar `UsuarioUnitOfWork` y migración de `usuarios` (E4.4), y conectar servicios/routers de catálogo (E5.1–E5.3) y pedidos (E6.1–E6.4). | Verificar commit/rollback/close y sesión compartida en módulos de catálogo y pedidos. | Completada (E3.1–E3.3 verificadas en SQLite) |
| 4. Autenticación y usuarios | 10 | E4.1–E4.4, E7.2, E8.1, E9.4 | `unidad9_backend/app/modules/usuarios/` (cookie `access_token` HttpOnly, bcrypt, PyJWT) + `unidad9_frontend` (`axiosInstance`, `authStore` `persist`/`partialize`, `ProtectedRoute`, `LoginPage`/`RegisterPage` TanStack Form, `AdminUsersPage`) y tests TP9. | Separar `app/core/{security,deps}.py` y `app/modules/auth/`, migrar a `passlib`+`python-jose` (claims `role`/`type="access"`), `OAuth2PasswordBearerWithCookie`, `require_role` con `UserPublic`, `/api/v1/auth/token` `{"message": "Login exitoso"}`, `/api/v1/admin/usuarios` completo y bloqueo `400` auto-desactivación; handler frontend en `400` desactivada y ocultar `"Desactivar"` propio. | Recorrido registro/login/logout/me y errores/permisos. | Pendiente |
| 5. API de catálogo | 10 | E5.1–E5.3, E9.2 | Routers/services limpiados del parcial. | Contratos TPI, categoría única, paginación, PATCH y baja. | Verificar códigos, schemas, filtros, permisos y 204. | Pendiente |
| 6. API de pedidos y reglas de negocio | 15 | E6.1–E6.4, E10.1 | Módulo nuevo a construir. | RN-01–06, transacciones, permisos y resumen. | Caso segunda línea sin stock, rollback, transiciones y restitución. | Pendiente |
| 7. Frontend cliente | 10 | E8.1–E8.4 | `LoginPage`/`RegisterPage` (`@tanstack/react-form`) y `UnauthorizedPage` probados en `unidad9_frontend/src/pages/`. | Migrar a `src/features/auth/` (`RegisterPage` vía `api/` + Query), `LoginPage` redirigiendo a `location.state?.from?.pathname ?? '/'`, `UnauthorizedPage` con enlace a `'/'`, catálogo público en `/`, `cartStore`, checkout y mis pedidos. | Navegador: registro, compra, detalle y cancelación. | Pendiente |
| 8. Frontend panel administración | 10 | E9.1–E9.4 | `ProtectedRoute` (con `children`) y `AdminUsersPage` (tabla con `useState`/`useEffect`) en `unidad9_frontend`. | `ProtectedRoute` con `<Outlet />`, `AdminUsuariosPage` con TanStack Query/Table ocultando `"Desactivar"` en fila propia (consumiendo `/api/v1/admin/usuarios`), más resumen, ABM catálogo y gestión de pedidos (`limit=100`). | Recorrido admin por pantallas y permisos. | Pendiente |
| 9. Frontend: estado, datos y sesión | 10 | E7.1–E7.3, E8.1–E9.4 | `axiosInstance.ts` (`withCredentials`, `setUnauthorizedHandler`, `error.cause`), `authStore.ts` (`persist`+`partialize`, `logout` `try/finally`), `QueryClient` y Vitest (`src/test/`) en `unidad9_frontend`. | Organizar `src/shared/api/{axiosInstance,handleApiError,queryClient}.ts`, `src/features/`, `src/store/`, `src/routes/` con alias `@/`, `timeout: 15_000`, `VITE_API_URL` con `/api/v1`, handler en `400` `"Cuenta de usuario desactivada"`, `authStore` en español (`usuario`/`cargando`) y `cartStore` persistido. | Inspección de red, invalidaciones y persistencia sin JWT. | Pendiente |
| 10. Calidad y entrega | 5 | E10.1–E10.3 | Documentación y configuración base. | TS estricto, README ejecutable manualmente sin `setup.sh`, URL pública real, corrida final `pytest`/`Vitest` en `E10.2` y exclusión/limpieza de `tests/` descartable recién en `E10.3` para `.zip` (`CE-01`). | Máquina limpia sin `setup.sh`; confirmar ZIP limpio, repo y video públicos. | Pendiente |

### 5.2 Reglas de negocio

| Regla | Tareas | Evidencia existente | Brecha y comprobación futura | Estado |
|---|---|---|---|---|
| RN-01 Crear pedido transaccional | E6.1, E10.1 | Sin evidencia de pedidos TPI. | Verificar ítems únicos, producto vendible, stock, snapshots, total y rollback total si falla una línea. | Pendiente |
| RN-02 Transiciones | E6.2, E9.3 | Sin máquina TPI acreditada. | Probar transiciones permitidas, 400 inválida y terminales inmutables. | Pendiente |
| RN-03 Restitución | E6.2–E6.3, E8.4, E9.3 | Sin evidencia de cancelación de pedidos. | Confirmar restitución en misma transacción y una sola vez. | Pendiente |
| RN-04 Permisos | E4.3, E6.3, E7.2 | Sin evidencia de permisos TPI. | Cliente propio/PENDIENTE; admin todos/no terminal; ajeno 403. | Pendiente |
| RN-05 Inmutabilidad | E2.2, E6.1, E6.3 | E2.2 completada: `DetallePedido` persiste snapshots (`nombre_producto`, `precio_unitario`, `subtotal`) inmutables ante cambios posteriores en `Producto` y `pedidos/schemas.py` omite schemas de edición/borrado (`test_models.py`, `test_pedidos_schema.py` en verde). | Verificar persistencia transaccional y ausencia de endpoints de edición/borrado en E6.1 y E6.3. | Pendiente |
| RN-06 Datos del pedido | E6.1, E8.3 | Sin checkout TPI acreditado. | Schema rechaza pago distinto y dirección fuera de 5–200. | Pendiente |

### 5.3 Entregables CE-01–CE-07

La extracción de la consigna trunca la etiqueta **CE-04** junto a la línea del seed; aquí se identifica como el ítem de **seed** (`python -m app.db.seed`), sin inventar un entregable adicional.

| Ítem | Entrega normativa | Tareas | Evidencia existente | Brecha / comprobación futura | Estado |
|---|---|---|---|---|---|
| CE-01 | ZIP sin `node_modules`, `venv`, `.env` ni suite de pruebas descartable (`foodstore-backend/tests/`, `foodstore-frontend/src/__tests__/`, `.pytest_cache/`, `coverage/`), excluida recién en `E10.3`; repositorio GitHub público y URL en README raíz. | E10.2, E10.3 | Sin URL TPI comprobada; suites `tests/` de TP9 son red de verificación a migrar y mantener activas hasta `E10.2`. | Preparar ZIP limpio en `E10.3` (excluyendo/limpiando `tests/` migradas, `.pytest_cache/` y `coverage/` recién en esa etapa) y verificar acceso público; registrar URL real. | Pendiente de publicación |
| CE-02 | README raíz con guía manual autónoma (Opción B) como camino normativo sin depender de `setup.sh` (auxiliar opcional): requisitos, instalación/ejecución backend/frontend, variables y usuario seed admin. | E0.2, E10.3 | README raíz actualizado; guía en máquina limpia pendiente. | Seguir guía manual en máquina limpia sin `setup.sh` y documentar usuario TPI solo tras implementar seed. | Pendiente |
| CE-03 | `backend/.env.example` y `frontend/.env.example` completos y listos desde H1 para `cp .env.example .env` sin `setup.sh`. | E0.2, E1.1, E7.1 | `foodstore-backend/.env.example` completado con las 5 variables normativas y validado vía `cp .env.example .env` + `Settings` (E1.1); `foodstore-frontend/.env.example` aún omite `/api/v1` en `VITE_API_URL`. | Completar `foodstore-frontend/.env.example` (E7.1) y validar variables consumidas por frontend mediante copia manual directa. | Pendiente |
| CE-04 (etiqueta truncada en PDF: seed) | `python -m app.db.seed` invocable directamente de forma manual sin depender de `setup.sh`; carga admin, categorías y productos. | E1.3 | TP9 solo cuenta con `seed_unidades_medida` y `seed_test_admin` para `APP_ENV=test`; seed TPI pendiente. | Ejecutar manualmente sin `setup.sh`, verificar idempotencia, admin, ≥3 categorías y ≥8 productos con stock. | Pendiente |
| CE-05 | Instalar backend (`pip install -r requirements.txt`) y ejecutar `uvicorn app.main:app` (`create_all_tables()` en `lifespan`) directamente sin `setup.sh` y sin errores; `/docs` contiene endpoints. | E1.1–E1.2, E10.1 | `pip install -r requirements.txt` y `pip check` verificados en `.venv` (E1.1); `app/core/database.py`, `app/main.py` (`/api/v1`, `create_all_tables()` en `lifespan`, CORS, `/api/v1/health`, `/docs`, `/redoc`) y arranque real `uvicorn app.main:app` sobre SQLite verificados (E1.2). | Completar módulos/endpoints TPI y validar arranque manual limpio en PostgreSQL (E10.1) sin `setup.sh` con revisión completa de `/docs`. | Pendiente |
| CE-06 | `pnpm install`, `pnpm build`, `pnpm dev` directamente sin `setup.sh` y sin errores, con `Vitest` operativo hasta `E10.2`. | E7.1–E9.4, E10.1 | `unidad9_frontend` compila con Vite 6 / TS 5.7 en estructura plana sin alias `@/`. | Migrar a features + alias `@/` (TS ≥5.9, Vite ≥7), ejecutar comandos manuales desde H1 hasta entrega sin `setup.sh` y recorrer cliente/admin. | Pendiente |
| CE-07 | Video público 10–15 min: cámara al inicio, registro, compra cliente, gestión admin y cancelación con restitución. | E10.1, E10.3 | No hay video disponible; `presentation/mindmap_presentacion.mmd` es apoyo local opcional del guion previsto, no evidencia de grabación. | Grabar, publicar y enlazar desde README. | Pendiente de grabación |

### 5.4 Cierre y evidencia

Cada evidencia futura registra hito/tareas, escenario, resultado observado y checks afectados. Ni los hitos ni este checklist están verificados hoy.