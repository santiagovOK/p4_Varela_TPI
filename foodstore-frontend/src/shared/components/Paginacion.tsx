/**
 * Control de paginación accesible reutilizable en catálogos y listados paginados.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Tabla "Componentes compartidos — shared/components/" (pág. 18): `Paginacion`.
 * - Convenciones API REST (`skip`, `limit`, `total`, pág. 10) y rutas `/` y `/mis-pedidos` (págs. 19–20).
 */
import { Button } from '@/shared/ui'

export interface PaginacionProps {
  total?: number
  skip?: number
  limit?: number
  currentPage?: number
  totalPages?: number
  onPageChange: (nextValue: number) => void
  className?: string
}

/**
 * Navegación de páginas compatible con paginación por desplazamiento (`skip`/`limit`/`total`)
 * o por número de página (`currentPage`/`totalPages`).
 */
export function Paginacion({
  total,
  skip,
  limit,
  currentPage,
  totalPages,
  onPageChange,
  className = '',
}: PaginacionProps) {
  const isOffsetMode = skip !== undefined && limit !== undefined
  const safeLimit = Math.max(1, limit ?? 20)

  const computedTotalPages = Math.max(
    1,
    totalPages ??
      (total !== undefined ? Math.ceil(Math.max(0, total) / safeLimit) : 1),
  )

  const rawPage =
    currentPage ??
    (isOffsetMode ? Math.floor(Math.max(0, skip) / safeLimit) + 1 : 1)
  const computedCurrentPage = Math.min(computedTotalPages, Math.max(1, rawPage))

  const isFirstPage = computedCurrentPage <= 1
  const isLastPage = computedCurrentPage >= computedTotalPages

  function goToPage(targetPage: number) {
    const clampedPage = Math.min(computedTotalPages, Math.max(1, targetPage))
    if (isOffsetMode) {
      onPageChange((clampedPage - 1) * safeLimit)
      return
    }
    onPageChange(clampedPage)
  }

  return (
    <nav
      aria-label="Paginación"
      className={`flex flex-wrap items-center justify-between gap-3 pt-2 ${className}`.trim()}
    >
      <div className="flex items-center gap-2 text-sm text-slate-600">
        <span aria-current="page" className="font-medium text-slate-900">
          Página {computedCurrentPage} de {computedTotalPages}
        </span>
        {total !== undefined && (
          <span className="text-slate-500">({total} resultados)</span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={isFirstPage}
          onClick={() => goToPage(computedCurrentPage - 1)}
        >
          Anterior
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={isLastPage}
          onClick={() => goToPage(computedCurrentPage + 1)}
        >
          Siguiente
        </Button>
      </div>
    </nav>
  )
}
