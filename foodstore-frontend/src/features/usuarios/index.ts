/**
 * Barrel público de la feature `usuarios`.
 * Trazabilidad (`docs/consignas_tpi.pdf`): sección "Arquitectura por features" (págs. 17–18).
 */
export { activarUsuario, desactivarUsuario, getUsuariosAdmin } from './api/usuariosApi'
export { UsuariosTable } from './components/UsuariosTable'
export { ADMIN_USUARIOS_QUERY_KEY, useUsuarios } from './hooks/useUsuarios'
export { AdminUsuariosPage } from './pages/AdminUsuariosPage'
export type { UserCreate, UserPublic, UserRole } from './types/usuario.types'
