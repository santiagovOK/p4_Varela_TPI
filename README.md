# Trabajo Práctico Integrador — Food Store: Sistema de pedidos de comida

**Materia:** Programación IV (TUPaD - UTN).  
**Estudiante:** Varela, Santiago Octavio  
**Email institucional:** santiago.varela@tupad.utn.edu.ar

- **Repositorio GitHub:** https://github.com/santiagovOK/p4_Varela_TPI
- **Consigna normativa:** [consignas_tpi.pdf](docs/consignas_tpi.pdf)
- **Modelo objetivo:** [UML Food Store](docs/tpi_UML_Food_Store.svg)
- **Plan, arquitectura y trazabilidad:** [resolucion_tpi.md](docs/resolucion_tpi.md)
- **Diagrama RBAC y seguridad:** [diagrama_rbac.mmd](docs/diagrama_rbac.mmd)

## Video explicativo

- **Link Principal (YouTube):** https://www.youtube.com/watch?v=hduuk1okaTI
- **Link Opción B (Google Drive):** https://drive.google.com/file/d/1DE2IddkjzipM4nxfFn5FSNj3x1cydQMR/view?usp=sharing

- [Trabajo Práctico Integrador — Food Store: Sistema de pedidos de comida](#trabajo-práctico-integrador--food-store-sistema-de-pedidos-de-comida)
  - [Video explicativo](#video-explicativo)
  - [Descripción general del sistema](#descripción-general-del-sistema)
  - [Requisitos del entorno](#requisitos-del-entorno)
  - [Instalación y ejecución manual (Guía normativa autónoma)](#instalación-y-ejecución-manual-guía-normativa-autónoma)
    - [1. Backend (`foodstore-backend/`)](#1-backend-foodstore-backend)
    - [2. Frontend (`foodstore-frontend/`)](#2-frontend-foodstore-frontend)
  - [Variables de entorno](#variables-de-entorno)
    - [Backend (`foodstore-backend/.env`)](#backend-foodstore-backendenv)
    - [Frontend (`foodstore-frontend/.env`)](#frontend-foodstore-frontendenv)
  - [URLs principales del sistema](#urls-principales-del-sistema)
  - [Elementos adicionales respecto al cumplimiento estricto de las consignas](#elementos-adicionales-respecto-al-cumplimiento-estricto-de-las-consignas)

## Descripción general del sistema

**Food Store** es una aplicación web full-stack para la gestión de pedidos de comida, organizada en dos proyectos independientes comunicados vía API REST bajo `/api/v1`:

- **Backend (`foodstore-backend/`):** FastAPI + SQLModel + PostgreSQL (o SQLite en desarrollo local), con arquitectura en capas (`Routers -> Services -> UnitOfWork -> Repositories -> Models`), autenticación JWT en cookie `HttpOnly` (`access_token`), control de acceso basado en roles (`user` / `admin`) y gestión transaccional de pedidos y stock.
- **Frontend (`foodstore-frontend/`):** React 19 + TypeScript estricto (`strict: true`) + Vite + Tailwind CSS v4, organizado por `features/` (`auth`, `categorias`, `productos`, `usuarios`, `pedidos`), estado remoto con TanStack Query v5, formularios con TanStack Form v1, tablas administrativas con TanStack Table v8 y estado global con Zustand v5.

Guías específicas de cada subproyecto: [backend](foodstore-backend/README.md) y [frontend](foodstore-frontend/README.md).

## Requisitos del entorno

- **Python:** `>= 3.11`
- **Node.js:** `>= 20.19`
- **pnpm:** `>= 9`
- **Base de datos:** PostgreSQL `>= 15` (recomendado en producción/evaluación) o SQLite local (`sqlite:///./dev.db`) para pruebas rápidas.

## Instalación y ejecución manual (Guía normativa autónoma)

Los siguientes pasos permiten instalar, inicializar y ejecutar el sistema completo de forma manual y autónoma desde una máquina limpia, sin depender de `setup.sh` (el cual se conserva únicamente como utilidad auxiliar opcional).

### 1. Backend (`foodstore-backend/`)

Desde la raíz del repositorio:

```bash
cd foodstore-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Si utiliza PostgreSQL, verifique o ajuste `DATABASE_URL` en `foodstore-backend/.env`. Para desarrollo rápido con SQLite local puede usar `DATABASE_URL=sqlite:///./dev.db`.

Cargue los datos iniciales de forma idempotente (crea tablas si no existen, el usuario administrador por defecto, 4 categorías y 8 productos con stock positivo):

```bash
python -m app.db.seed
```

Credenciales del administrador generado por el seed:
- **Usuario:** `admin`
- **Contraseña:** `Admin1234!`

Inicie el servidor API en el puerto `8000`:

```bash
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend (`foodstore-frontend/`)

En una nueva terminal, desde la raíz del repositorio:

```bash
cd foodstore-frontend
cp .env.example .env
pnpm install
pnpm build
pnpm dev
```

El archivo `foodstore-frontend/.env.example` ya define `VITE_API_URL=http://localhost:8000/api/v1`.

## Variables de entorno

### Backend (`foodstore-backend/.env`)

| Variable | Descripción | Valor por defecto en `.env.example` |
|---|---|---|
| `DATABASE_URL` | Cadena de conexión SQLAlchemy/SQLModel (PostgreSQL o SQLite) | `postgresql+psycopg2://postgres:postgres@localhost:5432/foodstore` |
| `SECRET_KEY` | Clave secreta para firmar tokens JWT (`min_length=32`) | `foodstore_dev_secret_key_change_in_production_32chars` |
| `ALGORITHM` | Algoritmo de firma JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración en minutos de la sesión JWT | `30` |
| `FRONTEND_ORIGIN` | Origen permitido por CORS con credenciales (`allow_credentials=True`) | `http://localhost:5173` |

### Frontend (`foodstore-frontend/.env`)

| Variable | Descripción | Valor por defecto en `.env.example` |
|---|---|---|
| `VITE_API_URL` | URL base de la API REST (incluye prefijo `/api/v1`) | `http://localhost:8000/api/v1` |

## URLs principales del sistema

| Servicio / Vista | URL | Acceso |
|---|---|---|
| Frontend — Catálogo público | `http://localhost:5173/` | Público |
| Frontend — Login y Registro | `http://localhost:5173/login` · `http://localhost:5173/register` | Público |
| Frontend — Carrito, Checkout y Mis Pedidos | `http://localhost:5173/carrito` · `/checkout` · `/mis-pedidos` | Cliente / Admin autenticado |
| Frontend — Panel Admin (Resumen, Categorías, Productos, Pedidos, Usuarios) | `http://localhost:5173/admin/resumen` · `/admin/categorias` · `/admin/productos` · `/admin/pedidos` · `/admin/usuarios` | Solo `admin` |
| Backend — Prefijo base API REST | `http://localhost:8000/api/v1` | REST JSON + Cookie `HttpOnly` |
| Backend — Documentación Swagger UI | `http://localhost:8000/docs` | Público |
| Backend — Documentación ReDoc | `http://localhost:8000/redoc` | Público |

## Elementos adicionales respecto al cumplimiento estricto de las consignas

Además de satisfacer íntegramente las diez rúbricas, las reglas de negocio (`RN-01` a `RN-06`) y los requisitos de arquitectura de [consignas_tpi.pdf](docs/consignas_tpi.pdf), el proyecto incorpora un conjunto de controles defensivos, validaciones de borde y medidas de robustez documental y técnica. El flujo completo de roles, guardias de ruta y barreras de autorización se detalla en el diagrama [docs/diagrama_rbac.mmd](docs/diagrama_rbac.mmd).

1. **Límite defensivo en notas de checkout (`NOTAS_MAX_LENGTH = 500`):**  
   Aunque la consigna define `notas` como campo opcional sin cota explícita, `foodstore-frontend/src/features/pedidos/validation/checkoutValidation.ts` establece `NOTAS_MAX_LENGTH = 500` y valida el texto tras `.trim()` en `validateNotas`, evitando envíos desmedidos desde el formulario de checkout.
2. **Cota de 72 bytes UTF-8 para `bcrypt` en frontend y backend:**  
   Dado que `bcrypt` trunca silenciosamente contraseñas mayores a 72 bytes, tanto el validador frontend (`TextEncoder` en `foodstore-frontend/src/features/auth/validation/authValidation.ts`) como el backend (`len(password.encode("utf-8")) > 72` en `foodstore-backend/app/core/security.py` y `foodstore-backend/app/modules/usuarios/schemas.py`) rechazan explícitamente contraseñas que superen los 72 bytes en UTF-8 (incluso con caracteres multibyte/emojis).
3. **Normalización a `null` (`None`) en notas vacías o compuestas solo por espacios:**  
   Tanto `CheckoutPage.tsx` (`notas: trimmedNotas.length > 0 ? trimmedNotas : null`) como `_normalizar_notas` en `foodstore-backend/app/modules/pedidos/service.py` recortan espacios externos con `.trim()`/`.strip()` y normalizan cadenas vacías o de puro espacio a `null` (`None`), garantizando persistencia limpia en base de datos.
4. **Sanitización de `imagen_url` (`isValidImageUrl`) y fallback `onError` sin loop de red:**  
   `ProductoCard.tsx` y `AdminProductosPage.tsx` validan las URLs de imagen mediante `isValidImageUrl` aceptando únicamente `https://`, `http://` o rutas locales `/img/...` (bloqueando esquemas peligrosos como `javascript:`, `data:`, `vbscript:`, rutas `//` o traversal `..`), y registran la URL fallida en `onError` para mostrar un fallback visual sin provocar reintentos ni bucles infinitos de red.
5. **Deduplicación de verificación de sesión (`activeCheck`) y control de generación (`authGeneration`):**  
   `foodstore-frontend/src/store/authStore.ts` deduplica llamadas concurrentes a `checkSession()` compartiendo una promesa `activeCheck`, y utiliza un contador monotónico `authGeneration` junto con un `WeakMap` (`requestGenerations` en `src/shared/api/axiosInstance.ts`) para descartar respuestas tardías o expiraciones de sesión pertenecientes a generaciones previas tras un `logout` o cambio de usuario.
6. **Bloqueo pesimista `with_for_update` (`SELECT ... FOR UPDATE`) en transacciones de stock y pedidos:**  
   `ProductoRepository` (`get_by_id(..., for_update=True)` y `get_activo_by_id(..., for_update=True)`) y `PedidoRepository` (`get_by_id(..., for_update=True)`) aplican `statement.with_for_update()` durante la creación de pedidos (`RN-01`), cambios de estado (`RN-02`) y cancelaciones con restitución de stock (`RN-03`), previniendo condiciones de carrera y sobreventa bajo concurrencia en PostgreSQL.