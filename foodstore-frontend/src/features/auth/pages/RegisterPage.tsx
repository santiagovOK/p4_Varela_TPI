/**
 * Página de registro de usuario cliente con `@tanstack/react-form` y mutación vía `useAuth`.
 * Trazabilidad (`docs/consignas_tpi.md`):
 * - Tablas "Auth y usuarios" (`POST /auth/register`), "Schemas" (`UserCreate`) y "Rutas y pantallas"
 *   (`/register`, págs. 11, 14, 18 y 19).
 */
import { useForm } from '@tanstack/react-form'
import { Link, useNavigate } from 'react-router-dom'

import { Button, Card, Input } from '@/shared/ui'

import { useAuth } from '../hooks/useAuth'
import type { RegisterPayload } from '../types/auth.types'
import {
  extractFieldError,
  validateEmail,
  validateFullName,
  validatePassword,
  validateUsername,
} from '../validation/authValidation'

/** Formulario accesible de alta de cuenta cliente sin simular sesión ante errores HTTP. */
export function RegisterPage() {
  const navigate = useNavigate()
  const { registerMutation } = useAuth()

  const defaultValues: RegisterPayload = {
    username: '',
    full_name: '',
    email: '',
    password: '',
  }

  const form = useForm({
    defaultValues,
    onSubmit: async ({ value }) => {
      try {
        const createdUser = await registerMutation.mutateAsync({
          username: value.username.trim(),
          full_name: value.full_name.trim(),
          email: value.email.trim(),
          password: value.password.trim(),
        })
        navigate('/login', {
          replace: true,
          state: { registeredUsername: createdUser.username },
        })
      } catch {
        // El error normalizado permanece en `registerMutation.error` conservando los campos.
      }
    },
  })

  return (
    <section className="mx-auto flex min-h-[70vh] max-w-md items-center justify-center py-8">
      <Card className="w-full">
        <div className="mb-6 space-y-1">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Crear cuenta</h1>
          <p className="text-sm text-slate-600">
            Completá tus datos para registrarte y realizar pedidos en Food Store.
          </p>
        </div>

        {registerMutation.error && (
          <div
            role="alert"
            className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm font-medium text-rose-700"
          >
            {registerMutation.error.message}
          </div>
        )}

        <form.Subscribe selector={(state) => [state.canSubmit, state.isSubmitting] as const}>
          {([canSubmit, isSubmitting]) => {
            const busy = isSubmitting || registerMutation.isPending

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
                        helperText="Entre 1 y 50 caracteres."
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
                  name="full_name"
                  validators={{
                    onChange: ({ value }) => validateFullName(value),
                    onSubmit: ({ value }) => validateFullName(value),
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
                        label="Nombre completo"
                        name={field.name}
                        type="text"
                        autoComplete="name"
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
                  name="email"
                  validators={{
                    onChange: ({ value }) => validateEmail(value),
                    onSubmit: ({ value }) => validateEmail(value),
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
                        label="Correo electrónico"
                        name={field.name}
                        type="email"
                        autoComplete="email"
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
                        autoComplete="new-password"
                        helperText="Mínimo 8 caracteres (máximo 72 bytes UTF-8)."
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
                  loadingText="Creando cuenta…"
                >
                  Registrarse
                </Button>
              </form>
            )
          }}
        </form.Subscribe>

        <p className="mt-5 text-center text-sm text-slate-600">
          ¿Ya tenés una cuenta?{' '}
          <Link
            to="/login"
            className="font-medium text-blue-600 hover:text-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded"
          >
            Iniciá sesión
          </Link>
        </p>
      </Card>
    </section>
  )
}
