import axios, { type InternalAxiosRequestConfig } from 'axios'

import { handleApiError, isDisabledAccountError } from './handleApiError'

const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1'

function resolveApiBaseUrl(rawUrl: string | undefined): string {
  const trimmed = rawUrl?.trim().replace(/\/+$/, '')
  if (!trimmed) {
    return DEFAULT_API_BASE_URL
  }
  return trimmed.endsWith('/api/v1') ? trimmed : `${trimmed}/api/v1`
}

/** URL base resuelta para las peticiones a la API REST del TPI. */
export const API_BASE_URL = resolveApiBaseUrl(
  import.meta.env.VITE_API_URL as string | undefined,
)

/** Instancia única de Axios configurada con cookie HttpOnly (`withCredentials: true`). */
export const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  timeout: 15_000,
})

type UnauthorizedHandler = (() => void) | null

let unauthorizedHandler: UnauthorizedHandler = null
let authGeneration = 0
let authGenerationGetter: (() => number) | null = null

const requestGenerations = new WeakMap<InternalAxiosRequestConfig, number>()
let installed = false

/** Registra el callback invocado cuando la sesión expira o es invalidada por el backend. */
export function setUnauthorizedHandler(handler: UnauthorizedHandler): void {
  unauthorizedHandler = handler
}

/** Retorna la generación de autenticación vigente. */
export function getAuthGeneration(): number {
  return authGenerationGetter ? authGenerationGetter() : authGeneration
}

/** Incrementa el contador interno de generación de autenticación. */
export function bumpAuthGeneration(): number {
  return ++authGeneration
}

/** Permite delegar la lectura de generación de autenticación a un store externo. */
export function setAuthGenerationGetter(getter: (() => number) | null): void {
  authGenerationGetter = getter
}

function extractNormalizedPath(
  config: Pick<InternalAxiosRequestConfig, 'url' | 'baseURL'> | undefined,
): string {
  const rawUrl = config?.url ?? ''
  let pathname = rawUrl.split('?')[0] ?? ''

  try {
    pathname = new URL(rawUrl, config?.baseURL ?? API_BASE_URL).pathname
  } catch {
    // Mantiene pathname extraído de rawUrl cuando no es una URL resoluble
  }

  return pathname.replace(/\/+$/, '').replace(/^\/api\/v1(?=\/|$)/, '')
}

function isAuthTokenPath(
  config: Pick<InternalAxiosRequestConfig, 'url' | 'baseURL'> | undefined,
): boolean {
  return extractNormalizedPath(config) === '/auth/token'
}

function isExcludedAuthPath(
  config: Pick<InternalAxiosRequestConfig, 'url' | 'baseURL'> | undefined,
): boolean {
  const path = extractNormalizedPath(config)
  return path === '/auth/token' || path === '/auth/me'
}

/**
 * Instala de manera idempotente los interceptores de request y response sobre `axiosInstance`.
 */
export function setupInterceptors(): void {
  if (installed) {
    return
  }
  installed = true

  axiosInstance.interceptors.request.use((config) => {
    if (config.headers) {
      if (typeof config.headers.delete === 'function') {
        config.headers.delete('Authorization')
      } else {
        delete config.headers.Authorization
      }
      if (
        !config.headers.Accept ||
        config.headers.Accept === 'application/json, text/plain, */*'
      ) {
        config.headers.Accept = 'application/json'
      }
    }

    requestGenerations.set(config, getAuthGeneration())
    return config
  })

  axiosInstance.interceptors.response.use(
    (response) => response,
    (error: unknown) => {
      const normalized = handleApiError(error)

      if (axios.isAxiosError(error)) {
        const config = error.config ?? error.response?.config
        const status = normalized.status
        const reqGen = config ? requestGenerations.get(config) : undefined
        const isCurrentGen = reqGen === undefined || reqGen === getAuthGeneration()

        if (isCurrentGen) {
          if (status === 401 && !isExcludedAuthPath(config)) {
            unauthorizedHandler?.()
          } else if (
            status === 400 &&
            isDisabledAccountError(normalized) &&
            !isAuthTokenPath(config)
          ) {
            unauthorizedHandler?.()
          }
        }
      }

      return Promise.reject(normalized)
    },
  )
}

setupInterceptors()
