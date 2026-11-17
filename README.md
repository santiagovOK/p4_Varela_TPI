# Trabajo Práctico Integrador — Food Store: Sistema de pedidos de comida

**Materia:** Programación IV (TUPaD - UTN).

- Consigna normativa: [consignas_tpi.md](docs/consignas_tpi.md) ([PDF](docs/consignas_tpi.pdf)).
- Modelo objetivo: [UML Food Store](docs/tpi_UML_Food_Store.svg).
- Plan y trazabilidad: [resolucion_tpi.md](docs/resolucion_tpi.md).

## Punto de partida y alcance TPI

Este repositorio parte de **la base heredada de los TPs de Unidad 9 y Unidad 10** tras la limpieza de los artefactos exclusivos del segundo parcial (unidades de medida, relación N:N `ProductoCategoria`, `stock_cantidad`, `hay_stock`, `anulado_at`). La [resolución](docs/resolucion_tpi.md) detalla qué se hereda de TP9/TP10, qué se adapta/migra (catálogo público, `UnitOfWork`, `authStore` con `persist`/`partialize`, `handleApiError` con `.cause`) y qué se construye nuevo (módulo `pedidos`, `cartStore`, checkout y paneles admin).

Directorios físicos actuales: `foodstore-backend/` y `foodstore-frontend/`. Guías de cada subproyecto: [backend](foodstore-backend/README.md) y [frontend](foodstore-frontend/README.md).

## Requisitos recomendados para ejecutar la base heredada

Como entorno reproducible, se recomienda **Python 3.12, PostgreSQL 16, Node.js 22 y pnpm 10** (coherentes con CI actual). Esto es una recomendación para esta base, no una garantía del script ni los mínimos normativos futuros del TPI. `setup.sh` actualmente acepta Python **≥3.11**, Node.js **≥18.18** y pnpm **≥8**; los requisitos objetivo TPI son distintos y están detallados en la [resolución](docs/resolucion_tpi.md). Las dependencias no están fijadas a las versiones normativas futuras.

## Preparación y ejecución

### Opción A: aprovisionamiento automatizado

Desde la raíz, `./setup.sh --help` muestra opciones sin aprovisionar. La ejecución normal de `./setup.sh` **no es un diagnóstico de solo lectura**: puede instalar herramientas/dependencias, crear o reutilizar `.venv` en la raíz y enlazarlo desde el backend, copiar `.env.example` a `.env`, validar/configurar conectividad de base de datos, crear tablas y ejecutar `app.db.seed` si está disponible. También puede iniciar servidores si se solicita `--start`. Revise sus efectos y opciones antes de ejecutarlo; no use opciones de instalación/BD si solo quiere consultar ayuda.

### Opción B: preparación manual

Los siguientes comandos se ejecutan desde la raíz. Requieren una instancia PostgreSQL accesible y una base `foodstore` configurada según el entorno local.

```bash
# Backend: crear el entorno Python en la raíz del repositorio
python3 -m venv .venv
.venv/bin/python -m pip install -r foodstore-backend/requirements.txt
cp foodstore-backend/.env.example foodstore-backend/.env
# Si corresponde, editar foodstore-backend/.env y ajustar DATABASE_URL.

# Frontend: copiar configuración y preparar paquetes
cp foodstore-frontend/.env.example foodstore-frontend/.env
pnpm --dir foodstore-frontend install
```

Inicie backend y frontend en terminales separadas, también desde la raíz:

```bash
(cd foodstore-backend && ../.venv/bin/python -m uvicorn app.main:app --reload --port 8000)
pnpm --dir foodstore-frontend dev
```

La API queda en `http://localhost:8000` y la aplicación Vite en `http://localhost:5173`; documentación API: `http://localhost:8000/docs`. El frontend actual usa `VITE_API_URL=http://localhost:8000` y agrega `/api/v1` en su código. No anteponga `/api/v1` a esa variable en la configuración heredada.

El paquete de orquestación de la raíz puede instalarse, si se desean sus scripts, ejecutando `pnpm install` desde la raíz. Sus scripts actuales incluyen `pnpm run dev`, `pnpm run dev:back`, `pnpm run dev:front`, `pnpm run build:front`, `pnpm run test:back` y `pnpm run test:front`. El script de backend raíz espera `.venv` en la raíz.

## Pruebas e infraestructura

Las carpetas de pruebas (`foodstore-backend/tests/` y `foodstore-frontend/src/__tests__/`) actúan como red de verificación interna (`pytest` + `TestClient` con `StaticPool` y `Vitest` / Testing Library) y se refinan en cada corte de contrato de la [resolución](docs/resolucion_tpi.md). Para la entrega final (`CE-01`), las carpetas de tests se excluyen explícitamente del `.zip`.

El hook local está en `.githooks/pre-commit`. Su ubicación en el repositorio no significa que esté instalado como hook activo en `.git/hooks`; no se afirma aquí que se haya configurado. Las exclusiones y verificaciones del hook son las existentes.

## Objetivo TPI pendiente

El objetivo normativo es el sistema de pedidos descrito en la consigna y el UML. La [resolución](docs/resolucion_tpi.md) organiza las migraciones futuras de backend, frontend, persistencia, autenticación, pedidos, pruebas proporcionales y entrega. No ejecute instrucciones futuras como si existieran: en particular, el seed TPI `python -m app.db.seed`, el usuario `admin`/`Admin1234!`, el login y la arquitectura objetivo son pendientes, no componentes disponibles hoy.

## Entrega académica

- Aprobación: **60/100 o más**.
- Si el proyecto no corre, se aplica el descuento del **30%** indicado por la consigna.
- Repositorio público del TPI: **Pendiente de publicación**.
- Video público de defensa: **Pendiente de grabación**.
- Antes de entregar, completar implementación y verificación contra la consigna; publicar el repositorio con URL real, preparar ZIP sin dependencias, entornos virtuales ni `.env`, y grabar un video público de **10–15 minutos**. El video debe comenzar mostrando al estudiante y recorrer registro, compra como cliente, gestión administrativa y cancelación con restitución de stock.

No se atribuye puntaje ni cumplimiento funcional en este estado documental.