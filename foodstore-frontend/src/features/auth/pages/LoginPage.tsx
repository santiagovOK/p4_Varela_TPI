/**
 * Página de inicio de sesión con `@tanstack/react-form` y mutación vía `useAuth`.
 * Trazabilidad (`docs/consignas_tpi.pdf`):
 * - Tablas "Rutas y pantallas" (`/login`), "Formularios" y "Estado, datos y sesión" (págs. 18–20).
 */
import { useForm } from '@tanstack/react-form'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { Button, Card, Input } from '@/shared/ui'

import { useAuth } from '../hooks/useAuth'
import type { LoginCredentials } from '../types/auth.types'
import {
  extractFieldError,
  validatePassword,
  validateUsername,
} from '../validation/authValidation'

interface LoginLocationState {
  from?: {
    pathname?: string
  }
  registeredUsername?: string
}

/** Formulario accesible de autenticación de usuario con redirección al origen o `'/'`. */
export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { loginMutation } = useAuth()

  const locationState = (location.state as LoginLocationState | null) ?? null
  const registeredUsername = locationState?.registeredUsername
  const redirectTo = locationState?.from?.pathname ?? '/'

  const defaultValues: LoginCredentials = {
    username: '',
    password: '',
  }

  const form = useForm({
    defaultValues,
    onSubmit: async ({ value }) => {
      try {
        await loginMutation.mutateAsync({
          username: value.username.trim(),
          password: value.password.trim(),
        })
        navigate(redirectTo, { replace: true })
      } catch {
        // El error normalizado permanece en `loginMutation.error` conservando los campos.
      }
    },
  })

  return (
    <section className="mx-auto flex min-h-[70vh] max-w-md items-center justify-center py-8">
      <Card className="w-full">
        <div className="mb-6 space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Iniciar sesión</h1>
          <p className="text-sm text-slate-600">
            Ingresá con tu usuario y contraseña para continuar en Food Store.
          </p>
        </div>

        {registeredUsername && (
          <div
            role="status"
            aria-live="polite"
            className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3.5 py-2.5 text-sm text-emerald-800"
          >
            Cuenta creada para <strong>{registeredUsername}</strong>. Ya podés iniciar sesión.
          </div>
        )}

        {loginMutation.error && (
          <div
            role="alert"
            className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm font-medium text-rose-700"
          >
            {loginMutation.error.message}
          </div>
        )}

        <form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting] as const}>
          {([canSubmit, isSubmitting]) => {
            const busy = isSubmitting || loginMutation.isPending

            return (
              <form
                noValidate
                aria-busy={busy}
                className="space-y-4"
                onSubmit={(event) => {
                  event.preventDefault()
                  event.stopPropagation()
                  void form.handleSubmit()
                }}
              >
                <form.Field
                  name="username"
                  validators={{
                    onChange: ({ value }) => validateUsername(value),
                    onSubmit: ({ value }) => validateUsername(value),
                  }}
                >
                  {(field) => {
                    const showError =
                      field.state.meta.isTouched || form.state.submissionAttempts > 0
                    const errorMessage = showError
                      ? extractFieldError(field.state.meta.errors)
                      : null

                    return (
                      <Input
                        label="Nombre de usuario"
                        name={field.name}
                        type="text"
                        autoComplete="username"
                        disabled={busy}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(event) => field.handleChange(event.target.value)}
                        error={errorMessage}
                      />
                    )
                  }}
                </form.Field>

                <form.Field
                  name="password"
                  validators={{
                    onChange: ({ value }) => validatePassword(value),
                    onSubmit: ({ value }) => validatePassword(value),
                  }}
                >
                  {(field) => {
                    const showError =
                      field.state.meta.isTouched || form.state.submissionAttempts > 0
                    const errorMessage = showError
                      ? extractFieldError(field.state.meta.errors)
                      : null

                    return (
                      <Input
                        label="Contraseña"
                        name={field.name}
                        type="password"
                        autoComplete="current-password"
                        disabled={busy}
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(event) => field.handleChange(event.target.value)}
                        error={errorMessage}
                      />
                    )
                  }}
                </form.Field>

                <Button
                  type="submit"
                  variant="primary"
                  className="w-full"
                  disabled={!canSubmit || busy}
                  isLoading={busy}
                  loadingText="Ingresando…"
                >
                  Ingresar
                </Button>
              </form>
            )
          }}
        </form.Subscribe>

        <p className="mt-5 text-center text-sm text-slate-600">
          ¿Todavía no tenés cuenta?{' '}
          <Link
            to="/register"
            className="font-medium text-blue-600 hover:text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded"
          >
            Registrate acá
          </Link>
        </p>
      </Card>
    </section>
  )
}
