# Food Store — Backend

Backend de Food Store TPI, desarrollado con FastAPI, SQLModel y PostgreSQL. La fuente normativa del TPI y su plan son [la consigna](../docs/consignas_tpi.pdf) y la [resolución TPI](../docs/resolucion_tpi.md).

## Punto de partida y migración

Este backend parte de **la base heredada de los TPs de Unidad 9 y Unidad 10** tras la limpieza de los artefactos exclusivos del segundo parcial (unidades de medida, relación N:N `ProductoCategoria`, `stock_cantidad`, `hay_stock`, `anulado_at` y `app/core/seed.py`).

La evolución TPI incorpora:
- Adaptación de `auth` y `usuarios` (JWT en cookie HttpOnly, bcrypt, `get_current_user` / `get_current_active_user` / `require_role`, CORS con `allow_credentials=True`).
- `BaseRepository[T]` y `UnitOfWork` estricto con `Session(engine, expire_on_commit=False)` y `model_validate` dentro del bloque `with`.
- Modelos y contratos UML para `Categoria` y `Producto` (categoría única `categoria_id`, `stock: int`, paginación `{total, items}`, lecturas `GET` públicas y escrituras admin).
- Módulo nuevo `pedidos` (`Pedido`, `DetallePedido`, `PedidoUnitOfWork`, `RN-01`..`RN-06`, máquina de 4 estados, `/pedidos/resumen`).
- Seed TPI idempotente en `app/db/seed.py` (`python -m app.db.seed`).

### Requisitos y configuración

Se recomienda Python 3.12 y PostgreSQL 16 (el entorno objetivo admite Python 3.11–3.13). Desde la raíz del repositorio:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r foodstore-backend/requirements.txt
cp foodstore-backend/.env.example foodstore-backend/.env
```

Ajuste `DATABASE_URL` y variables de entorno en `foodstore-backend/.env`. A continuación, desde la raíz:

```bash
(cd foodstore-backend && ../.venv/bin/python -m uvicorn app.main:app --reload --port 8000)
```

La API publica documentación en `http://localhost:8000/docs` y `http://localhost:8000/redoc`.

## Pruebas e infraestructura

La suite en `tests/` (`pytest` + `TestClient` con `StaticPool` en SQLite en memoria) se refina escalonadamente en cada corte de contrato de la [resolución TPI](../docs/resolucion_tpi.md). En la entrega final (`CE-01`), la carpeta `tests/` se excluye del `.zip`.
