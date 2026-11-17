# Food Store — Frontend

Cliente web de Food Store TPI, desarrollado con React 19, TypeScript estricto, Tailwind CSS 4 y Vite. Para la normativa y el plan de evolución TPI, consulte la [consigna](../docs/consignas_tpi.md) y la [resolución TPI](../docs/resolucion_tpi.md).

## Punto de partida y migración

Este frontend parte de **la base heredada de los TPs de Unidad 9 y Unidad 10** tras la limpieza de los artefactos exclusivos del segundo parcial (tipos y componentes de catálogo del parcial y consultas a `/api/v1/unidades-medida`).

La evolución TPI organiza `src/shared/`, `src/features/` (con barrel exports `index.ts` y alias `@/`), `src/store/` y `src/routes/`, integrando:
- Axios con `withCredentials: true`, `handleApiError.ts` preservando `error.cause`, y `setUnauthorizedHandler` para `401` y `400` `"Cuenta de usuario desactivada"`.
- `authStore` con `persist` + `partialize` (solo `usuario`, nunca JWT) y `cartStore` persistido.
- `ProtectedRoute` con `Outlet`, custom hooks con TanStack Query, formularios con TanStack Form y tablas admin con TanStack Table (`limit=100`).
- Catálogo público en `/`, carrito y checkout, *Mis pedidos* y paneles de administración.

### Requisitos y configuración

Se recomienda Node.js 22 y pnpm 10. Desde la raíz del repositorio:

```bash
cp foodstore-frontend/.env.example foodstore-frontend/.env
pnpm --dir foodstore-frontend install
pnpm --dir foodstore-frontend dev
```

La aplicación se sirve en `http://localhost:5173`.

## Pruebas e infraestructura

La suite en `src/__tests__/` (`Vitest` / Testing Library) se refina escalonadamente en cada corte de contrato de la [resolución TPI](../docs/resolucion_tpi.md). En la entrega final (`CE-01`), la carpeta `src/__tests__/` se excluye del `.zip`.
