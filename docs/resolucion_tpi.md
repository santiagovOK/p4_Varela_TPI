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
| **Base heredada (TP9 / TP10)** | **Backend:** módulos `usuarios` y `auth`, JWT en cookie `access_token` HttpOnly, hash `bcrypt`, dependencias `get_current_user` / `get_current_active_user` / `require_role`, CORS con `allow_credentials=True`, borrado lógico. **Frontend:** arquitectura por features con barrel exports `index.ts`, alias `@/`, `ProtectedRoute` con `Outlet`, instancia Axios con `withCredentials: true` e interceptores, custom hooks con TanStack Query. | E1.1–E1.2, E4.1–E4.4, E7.1–E7.2 |
| **Se adapta / migra** | **Dominio y limpieza:** retiro de ingredientes (TP9/TP10) y limpieza de artefactos del segundo parcial (`unidades_medida`, N:N `ProductoCategoria`, `anulado_at`, `stock_cantidad`, `hay_stock`). **Catálogo y acceso:** lecturas `GET` públicas de categorías activas y productos (`{total, items}`, `limit` hasta 100); escrituras solo `admin`. **Persistencia y errores:** `UnitOfWork` estricto con `Session(engine, expire_on_commit=False)` y `Modelo.model_validate(...)` dentro del bloque `with` en `categorias`, `productos` y `pedidos`; excepciones de dominio en Service traducidas a HTTP en Router. **Frontend auth/API:** `authStore` en `src/store/authStore.ts` reincorporando `persist` + `partialize` (solo `usuario`, nunca JWT); `handleApiError.ts` preservando `error.cause`; `setUnauthorizedHandler` manejando `401` (fuera de `/auth/token` y `/auth/me`) y `400` `"Cuenta de usuario desactivada"`. | E1.3, E2.1, E3.1–E3.2, E5.1–E5.3, E7.1–E7.2 |
| **Se construye nuevo** | **Backend:** módulo `pedidos` con reglas `RN-01`..`RN-06`, máquina de 4 estados (`PENDIENTE`, `EN_PREPARACION`, `ENTREGADO`, `CANCELADO`), `PedidoUnitOfWork` con sesión compartida sobre productos, endpoint `/pedidos/resumen` (declarado antes de `/{id}`). **Frontend:** `cartStore` persistido, catálogo público en `/` con búsqueda/filtro/paginación remota, carrito y checkout con TanStack Form, vista *Mis pedidos* y detalle con cancelación, paneles admin (resumen, ABM categorías/productos, gestión de pedidos y usuarios) con TanStack Table (`limit=100`). | E2.2, E3.3, E6.1–E6.4, E7.3, E8.1–E9.4 |
| **Testing continuo y entrega** | Suites `pytest` + `TestClient` (`StaticPool`) y `Vitest` / Testing Library refinadas escalonadamente en cada corte de contrato (`H1`..`H5`), excluyendo explícitamente las carpetas de tests del `.zip` final (`CE-01`). | E0.2, E10.1–E10.3 |

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

- **Estructura exacta de archivos**: `app/main.py`, núcleo compartido `app/core/{config,database,security,deps,unit_of_work,base_repository}.py`, módulos `app/modules/{auth,usuarios,categorias,productos,pedidos}/` (`auth/` con `router.py`, `service.py`, `schemas.py`; los cuatro módulos de dominio con `models.py`, `schemas.py`, `repository.py`, `unit_of_work.py`, `service.py`, `router.py`) y `app/db/seed.py`.
- **Configuración y CORS (`config.py`, `main.py`)**: `Settings(BaseSettings)` con `pydantic-settings`, `SECRET_KEY: str = Field(min_length=32)`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `DATABASE_URL` y `FRONTEND_ORIGIN`. Middleware CORS con `allow_origins=[settings.FRONTEND_ORIGIN]` (explícito, nunca `"*"`) y `allow_credentials=True`.
- **Capas, UoW y Repositorios**: Router valida transporte, obtiene Service con `Depends` y traduce excepciones de dominio; nunca abre UoW ni llama `session.commit()`. `UnitOfWork` abre `Session(engine, expire_on_commit=False)` en `__enter__` y ejecuta `commit()`/`rollback()` y `close()` en `__exit__`. Los Services abren `with self.uow as uow:`, aplican reglas y convierten/devuelven schemas con `Modelo.model_validate(objeto)` dentro del bloque `with`. Schemas `*Update` (`CategoriaUpdate`, `ProductoUpdate`) son parciales (`| None = None`) y se aplican con `model_dump(exclude_unset=True)`. `BaseRepository[T]` expone `get_by_id`, `get_all`, `add`, `delete`; repositorios de dominio implementan `get_by_username` y `get_by_email` (`usuarios`), `get_by_nombre` (`categorias`), `search` (`productos`, por nombre, categoría y disponible), y `list_by_usuario` y `count_by_estado` (`pedidos`). `PedidoUnitOfWork` comparte la sesión entre `pedidos` y `productos`.
- **Seguridad (`security.py`, `deps.py`)**: bcrypt con límite de 72 bytes UTF-8 validado en `UserCreate.password` (`Field(min_length=8, max_length=72)`). `OAuth2PasswordBearerWithCookie` extrae el JWT exclusivamente de la cookie HttpOnly `access_token` (rechaza `Authorization: Bearer`). Claims JWT obligatorios: `sub`, `role`, `type="access"`, `exp`. Cadena jerárquica: `get_current_user` (401 si falta cookie, token inválido/expirado, `type != "access"` o usuario inexistente) → `get_current_active_user` (400 `"Cuenta de usuario desactivada"` si `disabled=True`) → `require_role` (403 si rol no autorizado).
- **Seed TPI (`app/db/seed.py`)**: idempotente mediante `python -m app.db.seed`: admin `admin` / `Admin1234!`, rol `admin`, al menos 3 categorías y 8 productos con stock. Esto es objetivo E1.3, no comportamiento actual.

### 3.2 Frontend objetivo

React + TypeScript estricto (`strict: true`, sin `any`).

- **Estructura exacta de archivos**: `src/shared/{api,ui,components,layout}/` (`axiosInstance.ts`, `handleApiError.ts`, `queryClient.ts`; `Button`, `Card`, `Input`, `Modal`, `BadgeEstado`; `Paginacion`, `Skeleton`, `EstadoVacio`, `EstadoError`; `Navbar`, `MainLayout`), `src/features/{auth,categorias,productos,usuarios,pedidos}/` (cada una con `pages/`, `components/`, `hooks/`, `api/`, `types/` y barrel export `index.ts`, usando alias `@/`), `src/store/{authStore,cartStore}.ts`, `src/routes/{AppRouter,ProtectedRoute}.tsx` (`ProtectedRoute` con `Outlet`), `src/App.tsx`, `src/main.tsx` y `src/index.css`.
- **Axios y errores (`axiosInstance.ts`, `handleApiError.ts`)**: instancia única heredada de TP10 y adaptada con `baseURL = VITE_API_URL`, `withCredentials: true` y `timeout: 15_000`. Login envía formulario `application/x-www-form-urlencoded` vía `URLSearchParams` a `POST /auth/token` seguido de `GET /auth/me`. Callback desacoplado `setUnauthorizedHandler` (evita ciclos de importación entre Axios y store) limpia `authStore` ante `401` fuera de `/auth/token` y `/auth/me`, y ante `400` con `detail === "Cuenta de usuario desactivada"`. `handleApiError.ts` normaliza `detail` (string o array 422 de FastAPI) en `Error` preservando `error.cause` con el `AxiosError` original.
- **Estado y sesión (TanStack Query + Zustand 5)**: TanStack Query 5 con custom hooks por feature para estado remoto e invalidación; TanStack Form 1 para formularios; TanStack Table 8 para tablas admin (paginación local sobre `limit=100`; catálogo público pagina en servidor). Zustand 5 con selectores atómicos y `useShallow` (`zustand/react/shallow`); `authStore` en `src/store/authStore.ts` reincorpora `persist` + `partialize` guardando solo `usuario` (nunca JWT ni flags volátiles), y `cartStore` persiste el carrito. `checkSession()` es la única llamada de sesión permitida en `useEffect` al montar `App.tsx` (evita estado zombie de `usuario` persistido). `logout()` usa `try/finally` para llamar a `POST /auth/logout` y limpiar el estado local incondicionalmente. `VITE_API_URL` apunta a `http://localhost:8000/api/v1`.
- **Estilos, diseño responsive y accesibilidad (Tailwind CSS 4)**: `src/index.css` parte de `@import "tailwindcss";` preservando la paleta visual del parcial (`slate` para superficies/bordes/textos, `blue`/`indigo` para acciones principales y acentos, y semánticos `emerald`/`amber`/`rose` para estados de `BadgeEstado`, stock y errores). Diseño **mobile-first** y responsive (`sm:`, `md:`, `lg:`) con foco visible (`focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2`), semántica ARIA (`aria-label`, `aria-invalid`, `aria-describedby`, `aria-busy`, `aria-live`, `aria-modal`, `role="alert"/"status"/"dialog"`) y contraste accesible en todos los componentes de `src/shared/ui/` y pantallas.

### 3.3 Versiones y configuración objetivo

Versiones normativas, no instaladas/fijadas en esta actualización: Python 3.11–3.13; PostgreSQL ≥15; `fastapi[standard]>=0.115`; `sqlmodel>=0.0.22`; `psycopg2-binary` 2.9; `python-jose[cryptography]==3.5.0`, `passlib[bcrypt]==1.7.4`, `bcrypt==4.0.1`, `pydantic-settings` 2.x, `python-multipart==0.0.20`. Frontend: Node ≥20.19, React 19, TypeScript ≥5.9, Vite ≥7, Tailwind 4 (`@tailwindcss/vite`), TanStack Query 5, Form 1, Table 8, React Router DOM 7 (`BrowserRouter`), Zustand 5, Axios 1, pnpm ≥9. Fijar combinaciones exactas compatibles es E1.1/E7.1.

| Variable objetivo | Uso |
|---|---|
| `DATABASE_URL` | PostgreSQL; desarrollo local puede usar SQLite. |
| `SECRET_KEY` | Firma JWT, mínimo 32 caracteres (`Field(min_length=32)`). |
| `ALGORITHM` | Algoritmo JWT; ejemplo `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración, valor por defecto 30. |
| `FRONTEND_ORIGIN` | Origen CORS explícito, por ejemplo `http://localhost:5173`. |
| `VITE_API_URL` | Base Axios objetivo incluye `/api/v1`; hoy conserva la URL heredada sin prefijo. |

### 3.4 Base heredada, testing continuo e infraestructura

El punto de partida combina **la base heredada de los TPs de Unidad 9 y Unidad 10** (`auth`, `usuarios`, cookie HttpOnly, bcrypt, CORS con credenciales, arquitectura por features con barrel exports `index.ts`, alias `@/`, `ProtectedRoute` con `Outlet`, Axios con `withCredentials` e interceptores, custom hooks con TanStack Query) con la limpieza de los artefactos exclusivos del segundo parcial (`unidades_medida`, `ProductoCategoria`, `stock_cantidad`, `hay_stock`, `anulado_at`, `seed_unidades_medida`).

El testing continuo durante el desarrollo (`pytest` + `TestClient` con `StaticPool` en SQLite en memoria en backend; `Vitest` / Testing Library en frontend) se preserva y refina escalonadamente en cada corte de contrato (`H1`..`H5`) sobre los módulos Food Store (`auth`, `usuarios`, `categorias`, `productos`, `pedidos`). Aunque las pruebas automatizadas no son requisito académico evaluado en la rúbrica, aportan evidencia proporcional en cada incremento; **las carpetas de tests (`foodstore-backend/tests/` y `foodstore-frontend/src/__tests__/`) se excluyen explícitamente del `.zip` de entrega final (CE-01)** para no hacer pesado el proyecto.

### 3.5 Estrategia de ejecución e integración progresiva

Bottom-up significa construir cada recorrido desde modelos y persistencia hasta HTTP y UI, no completar horizontalmente todo el backend. Las épicas agrupan responsabilidades; los números de tarea y el orden del seguimiento local no son un orden topológico. `Dependencias` enumera condiciones de cierre de la tarea completa. Solo se inician porciones identificadas abajo cuando sus prerrequisitos reales están satisfechos. Una tarea parcialmente implementada queda `[EN CURSO]`, nunca `[COMPLETADA]`; los hitos no crean nuevas tareas ni IDs.

No se simulan APIs, repositorios ni permisos para declarar un hito logrado. No se montan routers, imports ni relaciones hacia módulos aún inexistentes. En H1 se integra la relación Categoria–Producto; `Producto.detalles` y los otros enlaces a pedidos se incorporan con E2.2, sin relaciones rotas ni entidades ficticias.

| Hito | Trabajo y condiciones concretas | Evidencia necesaria para avanzar |
|---|---|---|
| H1 — Walking skeleton público | Completar E1.1, E1.2, E2.1 (categoría/producto), E3.1, E3.2 y E7.1. Integrar solamente lecturas públicas de E5.1/E5.2, componentes de carga/vacío/error de E7.3 y primera pantalla de lectura de E8.2. Esas cuatro tareas permanecen en curso si falta su alcance completo. Usar datos reales de catálogo en BD de desarrollo; no depende del seed TPI, auth, entidades/API de pedidos ni E6.4. | Con PostgreSQL y navegador, un producto real atraviesa Repository/UoW → Service → API `/api/v1/productos` → Axios/Query → catálogo. Respuesta `{total,items}` y categoría coherentes, sin contrato N:N anterior. Cambiar el dato en BD y volver a consultar permite observarlo en pantalla. Comprobar también carga, vacío y error. |
| H2 — Catálogo completo y sesión | Completar E2.2, E4.1–E4.3, E5.1–E5.3, E1.3, E7.2/E7.3, E8.1/E8.2 y E9.2, respetando la matriz de cierre. E2.2 agrega modelos y relaciones de usuario/pedido/detalle, no exige todavía implementar sus operaciones. E1.3 exige su seed completo; no se declara terminado con datos manuales de H1. | Registro/login/logout y `/auth/me` reales; permisos de catálogo, búsqueda/filtros/paginación/carrito y ABM admin observables. Seed repetible con admin, ≥3 categorías y ≥8 productos; nombre de categoría no liberado tras baja y registros inactivos 404. |
| H3 — Compra y cancelación | Completar E3.3, E6.1–E6.3 y E8.3/E8.4 sobre H2. El resumen E6.4 no bloquea este recorrido. | Compra persistida con snapshots/total y stock descontado; lista/detalle propios y cancelación con restitución una sola vez. Caso de dos líneas, segunda sin stock: ni pedido ni descuento de la primera persisten. Error de checkout conserva formulario/carrito y no navega como éxito. |
| H4 — Administración restante | Completar E4.4, E6.4, E9.1, E9.3 y E9.4. Estas ramas pueden avanzar independientemente cuando sus dependencias reales estén disponibles; H3 no es una barrera artificial para el listado de usuarios. | Resumen, cambios de estado válidos/inválidos, permisos y activación/desactivación de usuarios verificados; no hay auto-desactivación. |
| H5 — Verificación y entrega | E10.1 verifica el sistema integrado; E10.2 cierra la alineación completa de automatización; E10.3 prepara entrega. | Evidencia actual por criterio, ejecución en máquina limpia y entregables normativos. No reutilizar resultados anteriores ni llamar a esta etapa primera integración. |

Orden interno para evitar ambigüedades: H2 ejecuta E2.2 → E4.1 → E4.2 → E4.3 → E5.1 → E5.2 → E5.3; E1.3 puede completarse después de E5.2 y antes de verificar el ABM. La rama frontend E7.2 puede avanzar tras E4.3; E7.3 puede completarse en paralelo; luego E8.1/E8.2 y E9.2 cuando estén sus dependencias. No hay dependencia del catálogo respecto del seed: datos de desarrollo de H1 permiten comprobar lecturas antes de E1.3. En H3: E3.3 → E6.1 → E6.2 → E6.3 → E8.3 → E8.4. En H4: E4.4 → E9.4 es independiente de E6.4 → E9.1/E9.3.

Todo corte de contrato integra en la misma unidad backend, consumidores, imports, tipos y pruebas afectadas. Se elimina la vía obsoleta; no se crean adaptadores temporales ni se conservan endpoints N:N. El corte de catálogo H1 integra coordinadamente las porciones de E2.1/E3.2/E5.1/E5.2/E7.1/E8.2 necesarias para arrancar una aplicación real; no se publica como incremento ejecutable un modelo nuevo con consumidores antiguos rotos. Antes de integrar cada incremento, se comprueban arranque, recorrido vertical y checks existentes afectados. En ese mismo corte se actualizan comprobaciones de tablas/unidades/N:N obsoletas; no se saltan, desactivan ni dejan CI fallando hasta E10.2. E10.2 progresa dentro de cada corte y solo se cierra tras E10.1; su dependencia final no bloquea los cambios previos de automatización. Aquí solo se documenta esa regla: no se edita setup/CI/aplicación ni se ejecutan sus procesos.

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
- **Acción:** alinear identidad y documentación operativa, preservando cómo corre hoy el catálogo.
- **Dependencias:** E0.1.
- **Archivos:** `README.md`, `foodstore-backend/README.md`, `foodstore-frontend/README.md`, `package.json`, `setup.sh`, `.github/workflows/ci.yml`, `.env.example` de cada subproyecto.
- **Consigna/alcance:** guía de base heredada y objetivo TPI pendiente; no cambiar comportamiento.
- **RN/HU:** HU-TPI-01–06 como objetivos, no evidencia.
- **Criterio de aceptación:** enlaces existentes y comandos actuales distinguidos de tareas futuras.
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
- **Acción:** fijar dependencias objetivo e implementar `Settings(BaseSettings)`.
- **Dependencias:** E0.2.
- **Archivos:** `foodstore-backend/requirements.txt`, `.env.example`, `app/core/config.py` (objetivo pendiente).
- **Consigna/alcance:** stack backend (`passlib[bcrypt]==1.7.4`, `bcrypt==4.0.1`, `python-jose[cryptography]==3.5.0`, `pydantic-settings`, `python-multipart==0.0.20`) y variables de sección 3.
- **RN/HU:** HU-TPI-01.
- **Criterio de aceptación:** `Settings(BaseSettings)` lee `DATABASE_URL`, `SECRET_KEY` (`Field(min_length=32)`), `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` y `FRONTEND_ORIGIN`; versiones fijadas y `.env.example` completo.
- **Estado:** [PENDIENTE].
- **Evidencia:** `.env.example` actual con `DATABASE_URL` heredada; no prueba Settings TPI.

#### E1.2 — Preparar engine, sesiones y aplicación API
- **Acción:** adaptar persistencia y arranque.
- **Dependencias:** E1.1.
- **Archivos:** `foodstore-backend/app/core/database.py`, `app/main.py` actuales; piezas objetivo pendientes.
- **Consigna/alcance:** PostgreSQL (`engine`, `create_all_tables`, `session_factory`), `/api/v1`, CORS explícito con `allow_origins=[settings.FRONTEND_ORIGIN]` y `allow_credentials=True` (nunca `"*"`), `/docs`, `/redoc`.
- **RN/HU:** HU-TPI-01–06.
- **Criterio de aceptación:** configuración TPI arranca API documentada y sesión reutilizable, integradas y verificables en H1.
- **Estado:** [PENDIENTE].
- **Evidencia:** existen módulos heredados; no certifican el contrato objetivo.

#### E1.3 — Implementar seed idempotente TPI
- **Acción:** sembrar admin, categorías y productos y migrar integración de setup/CI.
- **Dependencias:** E2.2, E4.1, E5.2.
- **Archivos:** `foodstore-backend/app/db/seed.py` (objetivo pendiente); `setup.sh`, `.github/workflows/ci.yml`.
- **Consigna/alcance:** `python -m app.db.seed`, admin/Admin1234!, ≥3 categorías y ≥8 productos con stock.
- **RN/HU:** HU-TPI-01, HU-TPI-04.
- **Criterio de aceptación:** seed repetible y consistente con cinco entidades; sustituye el seed heredado tras retirar unidades de medida. La aceptación completa corresponde a H2 con E2.2, E4.1 y E5.2; los datos manuales de H1 no la sustituyen ni el seed bloquea H1.
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
- **Estado:** [PENDIENTE].
- **Evidencia:** modelos heredados existentes; no conformes al UML TPI.

#### E2.2 — Agregar usuario, pedido y detalle
- **Acción:** implementar tres entidades y schemas restantes.
- **Dependencias:** E2.1.
- **Archivos:** módulos objetivo pendientes en `foodstore-backend/app/modules/usuarios/`, `pedidos/` y `auth/`.
- **Consigna/alcance:** cinco tablas totales; relaciones con nombres UML; snapshots y pedido no editable/borrable.
- **RN/HU:** RN-01, RN-05, HU-TPI-01, HU-TPI-03, HU-TPI-05, HU-TPI-06.
- **Criterio de aceptación:** Usuario, Pedido y DetallePedido con campos, defaults, relaciones y schemas exactos.
- **Estado:** [PENDIENTE].
- **Evidencia:** no se atribuye existencia de estas entidades TPI.

### Épica 3 — Repository y Unit of Work

#### E3.1 — Implementar abstracciones base
- **Acción:** añadir `BaseRepository[T]` y `UnitOfWork` base.
- **Dependencias:** E1.2.
- **Archivos:** `foodstore-backend/app/core/base_repository.py` y `app/core/unit_of_work.py` (objetivo pendiente).
- **Consigna/alcance:** `get_by_id`, `get_all`, `add`, `delete`; `__enter__` con `Session(engine, expire_on_commit=False)`, `__exit__` con commit/rollback/close.
- **RN/HU:** HU-TPI-03–06.
- **Criterio de aceptación:** abstracciones base construidas sobre fábrica de sesiones, sin esperar el modelo completo de pedidos; entrada abre `Session(engine, expire_on_commit=False)`; salida hace commit/close o rollback/close según excepción.
- **Estado:** [PENDIENTE].
- **Evidencia:** servicios heredados usan Session; no se declara UoW.

#### E3.2 — Añadir UoW/repositorios de categorías y productos
- **Acción:** conectar repositorios a la misma sesión de trabajo.
- **Dependencias:** E2.1, E3.1.
- **Archivos:** `app/modules/categorias/{repository,unit_of_work}.py`, `app/modules/productos/{repository,unit_of_work}.py` (objetivo pendiente).
- **Consigna/alcance:** métodos `get_by_nombre` (`categorias`) y `search` (`productos`); retirar commits de Services/Routers al migrar operaciones.
- **RN/HU:** HU-TPI-04.
- **Criterio de aceptación:** servicios usan `with self.uow as uow:` y devuelven schemas con `model_validate` dentro del bloque; Router no abre UoW ni llama `session.commit()`. Integración H1 del catálogo con contrato coordinado.
- **Estado:** [PENDIENTE].
- **Evidencia:** base actual recibe Session directamente.

#### E3.3 — Añadir repositorio/UoW de pedidos
- **Acción:** coordinar pedidos y productos dentro de unidad de trabajo.
- **Dependencias:** E2.2, E3.1, E3.2.
- **Archivos:** `app/modules/pedidos/{repository,unit_of_work}.py` (objetivo pendiente).
- **Consigna/alcance:** métodos `list_by_usuario`, `count_by_estado`; `PedidoUnitOfWork` con sesión compartida entre pedidos y productos.
- **RN/HU:** RN-01–05, HU-TPI-03, HU-TPI-05.
- **Criterio de aceptación:** integra con las entidades y repositorios reales de pedidos; operaciones de pedido y stock comparten transacción UoW.
- **Estado:** [PENDIENTE].
- **Evidencia:** módulo de pedidos no forma parte de base heredada indicada.

### Épica 4 — Seguridad, autenticación y usuarios

#### E4.1 — Implementar criptografía y JWT
- **Acción:** adaptar hash/verificación bcrypt (`passlib[bcrypt]==1.7.4`, `bcrypt==4.0.1`) y creación/validación JWT (`python-jose[cryptography]==3.5.0`) desde la base heredada de los TPs de Unidad 9 y Unidad 10.
- **Dependencias:** E2.2.
- **Archivos:** `app/core/security.py` y `app/modules/usuarios/schemas.py` (`UserCreate.password` con `max_length=72`).
- **Consigna/alcance:** claims `sub`, `role`, `type="access"`, `exp`; límite de 72 bytes UTF-8 de bcrypt.
- **RN/HU:** HU-TPI-01.
- **Criterio de aceptación:** contraseñas almacenadas como hash; `UserCreate.password` acotado a `min_length=8, max_length=72`; token nunca expuesto en cuerpo de login y `hashed_password` nunca serializado.
- **Estado:** [PENDIENTE].
- **Evidencia:** base heredada de TP9/TP10 requiere integración y verificación en Food Store.

#### E4.2 — Implementar endpoints de autenticación
- **Acción:** adaptar registro, token OAuth2, logout y perfil desde la base heredada de los TPs de Unidad 9 y Unidad 10.
- **Dependencias:** E4.1.
- **Archivos:** `app/modules/auth/{router,service,schemas}.py` (objetivo pendiente).
- **Consigna/alcance:** cookie `access_token` HttpOnly (30 min por defecto).
- **RN/HU:** HU-TPI-01.
- **Criterio de aceptación:** registro 201/409 (`UsuarioDuplicado`); credenciales 401; cuenta desactivada 400 (`"Cuenta de usuario desactivada"`); `/auth/me` y logout operativos.
- **Estado:** [PENDIENTE].
- **Evidencia:** endpoints de auth de TP9/TP10 requieren integración y verificación en Food Store.

#### E4.3 — Implementar dependencias de sesión y rol
- **Acción:** adaptar `OAuth2PasswordBearerWithCookie`, `get_current_user`, `get_current_active_user` y `require_role` desde la base heredada de los TPs de Unidad 9 y Unidad 10.
- **Dependencias:** E4.2.
- **Archivos:** `app/core/deps.py` (objetivo pendiente).
- **Consigna/alcance:** extracción exclusiva desde cookie `access_token` (rechaza `Authorization: Bearer`); backend hace cumplir permisos.
- **RN/HU:** HU-TPI-01, HU-TPI-04–06.
- **Criterio de aceptación:** 401 sesión inválida/ausente o `type != "access"`, 400 `"Cuenta de usuario desactivada"`, 403 rol no autorizado.
- **Estado:** [PENDIENTE].
- **Evidencia:** dependencias de TP9/TP10 requieren integración y verificación con módulos Food Store.

#### E4.4 — Gestionar usuarios desde admin
- **Acción:** adaptar listado, activación y desactivación de usuarios sobre el módulo `usuarios` heredado de los TPs de Unidad 9 y Unidad 10.
- **Dependencias:** E4.3.
- **Archivos:** `app/modules/usuarios/{models,schemas,repository,unit_of_work,service,router}.py` (objetivo pendiente).
- **Consigna/alcance:** métodos `get_by_username`, `get_by_email` en repositorio; operaciones solo admin.
- **RN/HU:** HU-TPI-06.
- **Criterio de aceptación:** idempotencia (200); inexistente 404 (`UsuarioNoEncontrado`); auto-desactivación 400.
- **Estado:** [PENDIENTE].
- **Evidencia:** módulo `usuarios` de TP9/TP10 requiere migración a UoW estricto y verificación TPI.

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
- **Acción:** dependencias, `shared/{api,ui,components,layout}`, `features/{auth,categorias,productos,usuarios,pedidos}`, `store/`, `routes/`, Axios, QueryClient y tipos.
- **Dependencias:** E0.1.
- **Archivos:** `foodstore-frontend/package.json`, `src/shared/api/{axiosInstance,handleApiError,queryClient}.ts`, `src/routes/AppRouter.tsx` (objetivo pendiente).
- **Consigna/alcance:** React 19/TS estricto (`strict: true`, sin `any`); URL API `VITE_API_URL` con `/api/v1`.
- **RN/HU:** HU-TPI-01–06.
- **Criterio de aceptación:** infraestructura común puede avanzar desde el contrato documental E0.1 y conectarse a lecturas H1; APIs de pedidos no son prerrequisito. `axiosInstance.ts` único con `withCredentials: true`, `timeout: 15_000`, callback desacoplado `setUnauthorizedHandler` y `handleApiError.ts` preservando `error.cause`; tipos concordantes con contratos disponibles y arquitectura por features; probar cada consumidor al integrarlo.
- **Estado:** [PENDIENTE].
- **Evidencia:** `App.tsx` actual usa fetch; no se presenta como Axios/Query.

#### E7.2 — Implementar authStore y rutas protegidas
- **Acción:** sesión, login (`URLSearchParams` + `/auth/me`), logout (`try/finally`), `checkSession` y guardas.
- **Dependencias:** E7.1, E4.3.
- **Archivos:** `src/store/authStore.ts`, `src/routes/{AppRouter,ProtectedRoute}.tsx`, `src/App.tsx` (objetivo pendiente).
- **Consigna/alcance:** Zustand 5 con selectores atómicos, `useShallow` y `persist`/`partialize` guardando solo `usuario`.
- **RN/HU:** HU-TPI-01.
- **Criterio de aceptación:** sesión/rutas protegidas dependen de auth y roles, no del ABM de usuarios; limpiar `usuario` vía `setUnauthorizedHandler` ante 401 fuera de `/auth/token` y `/auth/me` y 400 `"Cuenta de usuario desactivada"`; `checkSession()` único en `useEffect` al montar `App.tsx`; `logout()` con `try/finally`; JWT nunca persistido.
- **Estado:** [PENDIENTE].
- **Evidencia:** sesión frontend TPI no acreditada.

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
- **Acción:** formularios de autenticación y pantalla unauthorized.
- **Dependencias:** E7.2.
- **Archivos:** `features/auth/` objetivo pendiente.
- **Consigna/alcance:** TanStack Form, sesión confirmada por backend.
- **RN/HU:** HU-TPI-01.
- **Criterio de aceptación:** login/registro enviables por teclado; errores asociados al campo/operación; fallo no elimina entradas ni confirma sesión inexistente; login/registro operan con cookie y logout limpia store y redirige. Aplicar 3.6.
- **Estado:** [PENDIENTE].
- **Evidencia:** pantallas TPI no acreditadas.

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
- **Acción:** tabla con activación/desactivación.
- **Dependencias:** E7.2, E4.4.
- **Archivos:** `features/usuarios/` objetivo pendiente.
- **Consigna/alcance:** ocultar el botón "Desactivar" en la fila del usuario de la sesión.
- **RN/HU:** HU-TPI-06.
- **Criterio de aceptación:** activar/desactivar fallido conserva usuario/estado confirmado y muestra error; solo éxito confirma cambio e invalida datos; el botón "Desactivar" se oculta en la fila del usuario de la sesión. Aplicar 3.6.
- **Estado:** [PENDIENTE].
- **Evidencia:** UI de usuarios no acreditada.

### Épica 10 — Verificación y entrega

#### E10.1 — Verificación integral final del flujo TPI
- **Acción:** verificar el sistema integrado en PostgreSQL/navegador después de las comprobaciones por incremento y actualizar evidencia por criterio.
- **Dependencias:** E1.3, E8.4, E9.1, E9.2, E9.3, E9.4.
- **Archivos:** aplicación y matriz de evidencia.
- **Consigna/alcance:** registro, compra, administración, cancelación y restitución.
- **RN/HU:** RN-01–06; HU-TPI-01–06.
- **Criterio de aceptación:** verificación integral final posterior a comprobaciones por incremento; evidencia reproducible actual, sin reutilizar resultados del parcial.
- **Estado:** [PENDIENTE].
- **Evidencia:** no realizada por esta actualización documental.

#### E10.2 — Alinear automatización al sistema TPI
- **Acción:** adaptar setup/CI y suites de testing continuo (`pytest` + `TestClient` con `StaticPool` en backend; `Vitest`/Testing Library en frontend) a los módulos Food Store en cada corte de contrato y cerrar su alineación completa tras E10.1.
- **Dependencias:** E10.1.
- **Archivos:** `setup.sh`, `.github/workflows/ci.yml`, `tests/` (red de verificación interna).
- **Consigna/alcance:** retirar comprobaciones obsoletas de unidades/N:N y fases del parcial; actualizar referencias de tests a `auth`, `usuarios`, `categorias`, `productos` y `pedidos`.
- **RN/HU:** cobertura proporcional de RN-01–06 y HU-TPI-01–06.
- **Criterio de aceptación:** automatización y red de testing continuo reflejan la aplicación TPI sin gates heredados incompatibles; alineación completa cerrada después de E10.1.
- **Estado:** [PENDIENTE].
- **Evidencia:** automatización actual es heredada.

#### E10.3 — Preparar entrega normativa
- **Acción:** completar README raíz y materiales de entrega.
- **Dependencias:** E10.2.
- **Archivos:** `README.md`, `presentation/mindmap_presentacion.mmd` (apoyo local opcional del guion), ZIP de entrega, URL repositorio y video (pendientes).
- **Consigna/alcance:** repo público con URL real; ZIP sin `node_modules`, `venv`, `.env` ni carpetas de tests (CE-01); video público 10–15 min, cámara al inicio, registro, compra, administración y cancelación mostrando restitución.
- **RN/HU:** RN-01–06; HU-TPI-01–06.
- **Criterio de aceptación:** guía ejecutable en máquina limpia; ZIP limpio excluyendo dependencias, `.env` y carpetas de tests; el mindmap es apoyo local opcional, no dependencia de ejecución, entregable normativo ni evidencia de grabación; siete entregables trazados en sección 5.
- **Estado:** [PENDIENTE].
- **Evidencia:** publicación y video pendientes; no se inventan URLs.

## 5. Trazabilidad y verificación

La rúbrica asigna 100 puntos al código entregado; las ponderaciones siguientes son las de la consigna, no puntaje obtenido. Pruebas automatizadas no son requisito académico explícito. La columna evidencia distingue infraestructura heredada de cumplimiento TPI; la comprobación es futura.

### 5.1 Criterios de evaluación

| # / criterio | Pts | Tareas | Evidencia existente (base) | Brecha TPI | Comprobación futura | Estado |
|---|---:|---|---|---|---|---|
| 1. Backend: estructura y configuración | 10 | E1.1–E1.3, E10.2 | Base heredada de TP9/TP10 y limpieza del parcial. | Settings, versiones, CORS/arranque y seed TPI. | Inspección de capas, `.env.example`, ejecución de seed y API. | Pendiente |
| 2. Modelo de datos | 10 | E2.1–E2.2 | Usuario heredado de TP9/TP10; catálogo limpiado del parcial. | Cinco entidades/campos/relaciones UML y snapshots. | Contrastar modelos/DDL y respuestas con UML. | Pendiente |
| 3. Unit of Work y Repository | 10 | E3.1–E3.3 | Patrón base de TP9/TP10 a unificar. | BaseRepository, UoW (`expire_on_commit=False`) y Services transaccionales. | Verificar commit/rollback/close y sesión compartida. | Pendiente |
| 4. Autenticación y usuarios | 10 | E4.1–E4.4, E7.2, E8.1, E9.4 | Base de `auth`/`usuarios` de TP9/TP10. | Adaptación a `authStore` con `persist`/`partialize`, `400` desactivada y gestión admin. | Recorrido registro/login/logout/me y errores/permisos. | Pendiente |
| 5. API de catálogo | 10 | E5.1–E5.3, E9.2 | Routers/services limpiados del parcial. | Contratos TPI, categoría única, paginación, PATCH y baja. | Verificar códigos, schemas, filtros, permisos y 204. | Pendiente |
| 6. API de pedidos y reglas de negocio | 15 | E6.1–E6.4, E10.1 | Módulo nuevo a construir. | RN-01–06, transacciones, permisos y resumen. | Caso segunda línea sin stock, rollback, transiciones y restitución. | Pendiente |
| 7. Frontend cliente | 10 | E8.1–E8.4 | Base por features, alias `@/` y Axios de TP10. | Catálogo en `/`, `cartStore`, checkout y mis pedidos. | Navegador: registro, compra, detalle y cancelación. | Pendiente |
| 8. Frontend panel administración | 10 | E9.1–E9.4 | `ProtectedRoute` con `Outlet` de TP10. | Resumen, ABM, pedidos y usuarios con TanStack Table (`limit=100`). | Recorrido admin por pantallas y permisos. | Pendiente |
| 9. Frontend: estado, datos y sesión | 10 | E7.1–E7.3, E8.1–E9.4 | Axios `withCredentials` y hooks TanStack Query de TP10. | `handleApiError` con `.cause`, `setUnauthorizedHandler`, `authStore`/`cartStore` persistidos. | Inspección de red, invalidaciones y persistencia sin JWT. | Pendiente |
| 10. Calidad y entrega | 5 | E10.1–E10.3 | Documentación y configuración base. | TS estricto, README ejecutable, URL pública real y entrega sin `tests/` en `.zip`. | Máquina limpia; confirmar ZIP, repo y video públicos. | Pendiente |

### 5.2 Reglas de negocio

| Regla | Tareas | Evidencia existente | Brecha y comprobación futura | Estado |
|---|---|---|---|---|
| RN-01 Crear pedido transaccional | E6.1, E10.1 | Sin evidencia de pedidos TPI. | Verificar ítems únicos, producto vendible, stock, snapshots, total y rollback total si falla una línea. | Pendiente |
| RN-02 Transiciones | E6.2, E9.3 | Sin máquina TPI acreditada. | Probar transiciones permitidas, 400 inválida y terminales inmutables. | Pendiente |
| RN-03 Restitución | E6.2–E6.3, E8.4, E9.3 | Sin evidencia de cancelación de pedidos. | Confirmar restitución en misma transacción y una sola vez. | Pendiente |
| RN-04 Permisos | E4.3, E6.3, E7.2 | Sin evidencia de permisos TPI. | Cliente propio/PENDIENTE; admin todos/no terminal; ajeno 403. | Pendiente |
| RN-05 Inmutabilidad | E2.2, E6.1, E6.3 | Sin modelo de pedido TPI acreditado. | Verificar snapshots y total fijos; no existen endpoints de edición/borrado. | Pendiente |
| RN-06 Datos del pedido | E6.1, E8.3 | Sin checkout TPI acreditado. | Schema rechaza pago distinto y dirección fuera de 5–200. | Pendiente |

### 5.3 Entregables CE-01–CE-07

La extracción de la consigna trunca la etiqueta **CE-04** junto a la línea del seed; aquí se identifica como el ítem de **seed** (`python -m app.db.seed`), sin inventar un entregable adicional.

| Ítem | Entrega normativa | Tareas | Evidencia existente | Brecha / comprobación futura | Estado |
|---|---|---|---|---|---|
| CE-01 | ZIP sin `node_modules`, `venv`, `.env` ni carpetas de `tests` (excluidas del `.zip` para no hacer pesado el proyecto); repositorio GitHub público y URL en README raíz. | E10.3 | Sin URL TPI comprobada. | Preparar ZIP limpio y verificar acceso público; registrar URL real. | Pendiente de publicación |
| CE-02 | README raíz con requisitos, instalación/ejecución backend/frontend, variables y usuario seed admin. | E0.2, E10.3 | README raíz actualizado; guía en máquina limpia pendiente. | Seguir guía en máquina limpia y documentar usuario TPI solo tras implementar seed. | Pendiente |
| CE-03 | `backend/.env.example` y `frontend/.env.example` completos. | E0.2, E1.1, E7.1 | Ejemplos heredados presentes. | Completar y validar variables efectivamente consumidas por stack TPI. | Pendiente |
| CE-04 (etiqueta truncada en PDF: seed) | `python -m app.db.seed` carga admin, categorías y productos. | E1.3 | Seed TPI pendiente de implementación. | Ejecutar idempotencia y verificar admin, ≥3 categorías, ≥8 productos con stock. | Pendiente |
| CE-05 | Instalar backend y ejecutar uvicorn sin errores; `/docs` contiene endpoints. | E1.1–E1.2, E10.1 | Base backend heredada; sin certificación TPI. | Instalación/arranque limpio y revisión OpenAPI. | Pendiente |
| CE-06 | `pnpm install`, `pnpm build`, `pnpm dev` sin errores. | E7.1–E9.4, E10.1 | Frontend heredado, no evidencia del stack objetivo. | Ejecutar comandos en entrega y recorrer cliente/admin. | Pendiente |
| CE-07 | Video público 10–15 min: cámara al inicio, registro, compra cliente, gestión admin y cancelación con restitución. | E10.1, E10.3 | No hay video disponible; `presentation/mindmap_presentacion.mmd` es apoyo local opcional del guion previsto, no evidencia de grabación. | Grabar, publicar y enlazar desde README. | Pendiente de grabación |

### 5.4 Cierre y evidencia

Cada evidencia futura registra hito/tareas, escenario, resultado observado y checks afectados. Ni los hitos ni este checklist están verificados hoy.