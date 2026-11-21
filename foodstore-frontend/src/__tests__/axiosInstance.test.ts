import fs from 'node:fs'
import path from 'node:path'

import axios, {
  AxiosError,
  AxiosHeaders,
  type AxiosAdapter,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  API_BASE_URL,
  axiosInstance,
  bumpAuthGeneration,
  getAuthGeneration,
  setAuthGenerationGetter,
  setUnauthorizedHandler,
  setupInterceptors,
} from '@/shared/api/axiosInstance'
import { getHttpErrorStatus, handleApiError } from '@/shared/api/handleApiError'
import { queryClient } from '@/shared/api/queryClient'

const originalAdapter = axiosInstance.defaults.adapter

function createAxiosResponse(
  config: InternalAxiosRequestConfig,
  status: number,
  data: unknown,
): AxiosResponse {
  return {
    data,
    status,
    statusText: String(status),
    headers: {},
    config,
  }
}

function createAxiosHttpError(
  config: InternalAxiosRequestConfig,
  status: number,
  data: unknown,
): AxiosError {
  const response = createAxiosResponse(config, status, data)
  return new AxiosError(
    `Request failed with status code ${status}`,
    AxiosError.ERR_BAD_REQUEST,
    config,
    undefined,
    response,
  )
}

afterEach(() => {
  axiosInstance.defaults.adapter = originalAdapter
  setUnauthorizedHandler(null)
  setAuthGenerationGetter(null)
  vi.restoreAllMocks()
})

describe('axiosInstance y shared/api', () => {
  it('configura baseURL con /api/v1, withCredentials y timeout de 15s', () => {
    expect(API_BASE_URL).toMatch(/\/api\/v1$/)
    expect(axiosInstance.defaults.baseURL).toBe(API_BASE_URL)
    expect(axiosInstance.defaults.withCredentials).toBe(true)
    expect(axiosInstance.defaults.timeout).toBe(15_000)
    expect(axiosInstance.defaults.headers.common.Authorization).toBeUndefined()
  })

  it('setupInterceptors es idempotente y no duplica interceptores', () => {
    const requestHandlers = (
      axiosInstance.interceptors.request as unknown as { handlers: unknown[] }
    ).handlers
    const responseHandlers = (
      axiosInstance.interceptors.response as unknown as { handlers: unknown[] }
    ).handlers

    const initialReqCount = requestHandlers.filter(Boolean).length
    const initialResCount = responseHandlers.filter(Boolean).length

    setupInterceptors()
    setupInterceptors()

    expect(requestHandlers.filter(Boolean).length).toBe(initialReqCount)
    expect(responseHandlers.filter(Boolean).length).toBe(initialResCount)
  })

  it('interceptor de request normaliza Accept y elimina Authorization', async () => {
    let capturedHeaders: AxiosHeaders | undefined

    const mockAdapter: AxiosAdapter = async (config) => {
      capturedHeaders = AxiosHeaders.from(config.headers)
      return createAxiosResponse(config, 200, { ok: true })
    }
    axiosInstance.defaults.adapter = mockAdapter

    const response = await axiosInstance.get('/productos', {
      headers: { Authorization: 'Bearer token-indebido' },
    })

    expect(response.status).toBe(200)
    expect(response.data).toEqual({ ok: true })
    expect(capturedHeaders?.get('Authorization')).toBeUndefined()
    expect(capturedHeaders?.get('Accept')).toBe('application/json')
  })

  it('handleApiError normaliza detail string y 422 preservando error.cause', () => {
    const config = { headers: new AxiosHeaders() } as InternalAxiosRequestConfig

    const err404 = createAxiosHttpError(config, 404, { detail: 'Producto no encontrado' })
    const norm404 = handleApiError(err404)
    expect(norm404).toBeInstanceOf(Error)
    expect(norm404.message).toBe('Producto no encontrado')
    expect(norm404.cause).toBe(err404)
    expect(getHttpErrorStatus(norm404)).toBe(404)

    const err422 = createAxiosHttpError(config, 422, {
      detail: [{ msg: 'Campo requerido' }, { msg: 'Debe ser positivo' }],
    })
    const norm422 = handleApiError(err422)
    expect(norm422.message).toBe('Campo requerido; Debe ser positivo')
    expect(norm422.cause).toBe(err422)
    expect(getHttpErrorStatus(norm422)).toBe(422)
  })

  it('dispara unauthorizedHandler ante 401 en rutas protegidas y rechaza Error con cause', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)

    axiosInstance.defaults.adapter = async (config) => {
      throw createAxiosHttpError(config, 401, { detail: 'No autenticado' })
    }

    await expect(axiosInstance.get('/pedidos')).rejects.toMatchObject({
      message: 'No autenticado',
      status: 401,
    })

    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })

  it('no dispara unauthorizedHandler ante 401 en /auth/token ni /auth/me', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)

    axiosInstance.defaults.adapter = async (config) => {
      throw createAxiosHttpError(config, 401, { detail: 'Credenciales inválidas' })
    }

    await expect(axiosInstance.post('/auth/token')).rejects.toThrow('Credenciales inválidas')
    await expect(axiosInstance.get('/auth/me/')).rejects.toThrow('Credenciales inválidas')
    await expect(axiosInstance.get('/api/v1/auth/me?check=1')).rejects.toThrow(
      'Credenciales inválidas',
    )

    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('dispara unauthorizedHandler ante 400 "Cuenta de usuario desactivada" fuera de /auth/token', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)

    axiosInstance.defaults.adapter = async (config) => {
      throw createAxiosHttpError(config, 400, { detail: 'Cuenta de usuario desactivada' })
    }

    await expect(axiosInstance.get('/auth/me')).rejects.toThrow('Cuenta de usuario desactivada')
    expect(onUnauthorized).toHaveBeenCalledTimes(1)

    onUnauthorized.mockClear()
    await expect(axiosInstance.post('/auth/token')).rejects.toThrow('Cuenta de usuario desactivada')
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('nunca dispara unauthorizedHandler ante 403 Forbidden', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)

    axiosInstance.defaults.adapter = async (config) => {
      throw createAxiosHttpError(config, 403, { detail: 'Permisos insuficientes' })
    }

    await expect(axiosInstance.get('/admin/usuarios')).rejects.toThrow('Permisos insuficientes')
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('descarta disparos de unauthorizedHandler de peticiones de una generación obsoleta', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)

    const initialGen = getAuthGeneration()
    expect(typeof initialGen).toBe('number')

    axiosInstance.defaults.adapter = async (config) => {
      bumpAuthGeneration()
      throw createAxiosHttpError(config, 401, { detail: 'Sesión expirada tardía' })
    }

    await expect(axiosInstance.get('/productos')).rejects.toThrow('Sesión expirada tardía')
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('queryClient exporta instancia única con opciones por defecto configuradas', () => {
    const defaults = queryClient.getDefaultOptions().queries
    expect(defaults?.staleTime).toBe(1000 * 60 * 5)
    expect(defaults?.gcTime).toBe(1000 * 60 * 10)
    expect(defaults?.retry).toBe(1)
    expect(defaults?.refetchOnWindowFocus).toBe(false)
  })
})

describe('arquitectura modular por features', () => {
  it('verifica 5 features x 5 subcarpetas y barrels index.ts sin export *', () => {
    const featuresRoot = path.resolve(import.meta.dirname, '..', 'features')
    const features = ['auth', 'categorias', 'productos', 'usuarios', 'pedidos']
    const subfolders = ['pages', 'components', 'hooks', 'api', 'types']

    for (const feature of features) {
      const featureDir = path.join(featuresRoot, feature)
      expect(fs.existsSync(featureDir)).toBe(true)

      for (const subfolder of subfolders) {
        expect(fs.existsSync(path.join(featureDir, subfolder))).toBe(true)
      }

      const barrelPath = path.join(featureDir, 'index.ts')
      expect(fs.existsSync(barrelPath)).toBe(true)
      const barrelContent = fs.readFileSync(barrelPath, 'utf-8')
      expect(barrelContent).not.toMatch(/export\s+\*/)
    }

    expect(axios.isAxiosError(new AxiosError('test'))).toBe(true)
  })
})
