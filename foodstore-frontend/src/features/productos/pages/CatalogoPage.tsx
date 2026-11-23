/**
 * Página principal del catálogo público con búsqueda, filtro por categoría y paginación remota.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - HU-TPI-02 (págs. 12–14, 18–20): ruta `/`, búsqueda, filtro por categoría y paginación.
 */
import { useRef, useState, type ChangeEvent } from 'react'

import { useCategorias, type CategoriaRead } from '@/features/categorias'
import { EstadoError, EstadoVacio, Paginacion, Skeleton } from '@/shared/components'
import { Button, Input } from '@/shared/ui'
import { useAuthSession } from '@/store/authStore'

import { ProductoCard } from '../components/ProductoCard'
import { CATALOGO_DEFAULT_LIMIT, useProductos } from '../hooks/useProductos'
import type { ProductosPaginados } from '../types/producto.types'

const EMPTY_CATEGORIAS: readonly CategoriaRead[] = []

/** Vista pública de catálogo montada en `/` con control de carga, vacío y error de refetch. */
export function CatalogoPage() {
  useAuthSession()
  const [searchInput, setSearchInput] = useState('')
  const [categoriaId, setCategoriaId] = useState<number | undefined>(undefined)
  const [skip, setSkip] = useState(0)
  const confirmedDataRef = useRef<ProductosPaginados | undefined>(undefined)
  const limit = CATALOGO_DEFAULT_LIMIT

  const normalizedSearch = searchInput.trim()
  const hasActiveFilters = normalizedSearch.length > 0 || categoriaId !== undefined

  const { data: categoriasData } = useCategorias()
  const categorias = categoriasData ?? EMPTY_CATEGORIAS

  const { data, isLoading, isError, isRefetchError, isPlaceholderData, error, refetch } =
    useProductos({
      search: normalizedSearch,
      categoria_id: categoriaId,
      skip,
      limit,
      disponible: true,
    })

  if (data && !isPlaceholderData) {
    confirmedDataRef.current = data
  }

  const activeData = data ?? confirmedDataRef.current

  function handleSearchChange(event: ChangeEvent<HTMLInputElement>) {
    const nextValue = event.target.value
    setSearchInput(nextValue)
    if (nextValue.trim() !== normalizedSearch) {
      setSkip(0)
    }
  }

  function handleCategoriaChange(event: ChangeEvent<HTMLSelectElement>) {
    const rawValue = event.target.value
    const nextCategoria = rawValue ? Number(rawValue) : undefined
    setCategoriaId(nextCategoria)
    setSkip(0)
  }

  function handleResetFilters() {
    setSearchInput('')
    setCategoriaId(undefined)
    setSkip(0)
  }

  return (
    <section className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Catálogo de productos
        </h1>
        <p className="text-sm text-slate-600">
          Explorá los productos disponibles y agregalos a tu carrito.
        </p>
      </header>

      <div className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-end">
        <div className="flex-1">
          <Input
            label="Buscar productos"
            type="search"
            placeholder="Ej. Hamburguesa, Pizza..."
            value={searchInput}
            onChange={handleSearchChange}
          />
        </div>

        <div className="w-full space-y-1.5 sm:w-64">
          <label
            htmlFor="catalogo-categoria-select"
            className="block text-sm font-medium text-slate-700"
          >
            Categoría
          </label>
          <select
            id="catalogo-categoria-select"
            value={categoriaId ?? ''}
            onChange={handleCategoriaChange}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-1"
          >
            <option value="">Todas las categorías</option>
            {categorias.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.nombre}
              </option>
            ))}
          </select>
        </div>

        {hasActiveFilters && (
          <Button variant="secondary" onClick={handleResetFilters}>
            Limpiar filtros
          </Button>
        )}
      </div>

      {isLoading && !activeData ? (
        <Skeleton variant="card" count={6} label="Cargando catálogo de productos…" />
      ) : isError && !activeData ? (
        <EstadoError
          variant="alert"
          title="No se pudo cargar el catálogo"
          message={error?.message ?? 'Error al consultar los productos.'}
          onRetry={() => void refetch()}
        />
      ) : activeData ? (
        <div className="space-y-5">
          {(isError || isRefetchError) && (
            <EstadoError
              variant="inline-refetch"
              isRefetchError
              message={error?.message ?? 'No se pudo actualizar el catálogo.'}
              onRetry={() => void refetch()}
            />
          )}

          {activeData.items.length === 0 ? (
            <EstadoVacio
              title="No se encontraron productos"
              description={
                hasActiveFilters
                  ? 'No hay productos que coincidan con la búsqueda o categoría seleccionada.'
                  : 'Actualmente no hay productos disponibles en el catálogo.'
              }
              actionLabel={hasActiveFilters ? 'Limpiar filtros' : undefined}
              onAction={hasActiveFilters ? handleResetFilters : undefined}
            />
          ) : (
            <>
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                {activeData.items.map((producto) => (
                  <ProductoCard key={producto.id} producto={producto} />
                ))}
              </div>

              <Paginacion
                total={activeData.total}
                skip={skip}
                limit={limit}
                onPageChange={setSkip}
              />
            </>
          )}
        </div>
      ) : null}
    </section>
  )
}
