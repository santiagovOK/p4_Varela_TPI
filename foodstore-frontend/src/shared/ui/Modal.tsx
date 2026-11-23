/**
 * Diálogo modal controlado con accesibilidad WAI-ARIA y bloqueo durante envíos en curso.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Tabla "Componentes compartidos — shared/ui/" (pág. 18): `Modal`.
 */
import { useEffect, useId, type ReactNode } from 'react'

export interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: ReactNode
  footer?: ReactNode
  isSubmitting?: boolean
  busy?: boolean
  closeLabel?: string
}

/**
 * Modal controlado (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`).
 * Bloquea el scroll del documento mientras está abierto e impide cerrarse por `Escape`,
 * clic en el fondo o botón de cierre mientras `isSubmitting` o `busy` esté activo.
 */
export function Modal({
  isOpen,
  onClose,
  title,
  children,
  footer,
  isSubmitting = false,
  busy = false,
  closeLabel = 'Cerrar modal',
}: ModalProps) {
  const titleId = useId()
  const isBusy = Boolean(isSubmitting || busy)

  useEffect(() => {
    if (!isOpen) {
      return
    }

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !isBusy) {
        event.preventDefault()
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, isBusy, onClose])

  if (!isOpen) {
    return null
  }

  return (
    <div
      data-testid="modal-backdrop"
      onClick={() => {
        if (!isBusy) {
          onClose()
        }
      }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-busy={isBusy || undefined}
        onClick={(event) => event.stopPropagation()}
        className="w-full max-w-lg rounded-xl bg-white border border-slate-200 shadow-xl overflow-hidden"
      >
        <div className="flex items-center justify-between gap-4 border-b border-slate-100 px-5 py-4">
          <h2 id={titleId} className="text-lg font-semibold text-slate-900">
            {title}
          </h2>

          <button
            type="button"
            aria-label={closeLabel}
            disabled={isBusy}
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="h-5 w-5"
            >
              <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
            </svg>
          </button>
        </div>

        <div className="px-5 py-4 max-h-[75vh] overflow-y-auto">{children}</div>

        {footer && (
          <div className="flex items-center justify-end gap-2 border-t border-slate-100 bg-slate-50 px-5 py-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
