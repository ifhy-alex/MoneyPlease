import type { UseQueryResult } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, errorMessage } from '../api/client'
import { EmptyState, type EmptyKind } from '../decor/EmptyState'

interface Props {
  query: UseQueryResult<unknown>
  height: number
  empty: boolean
  emptyKind?: EmptyKind
  emptyTitle: string
  emptyText?: string
  /** Texto cuando la API responde 404 porque todavía no hay perfil guardado. */
  noProfileTitle?: string
  children: ReactNode
}

/** Marco común de las piezas de arte con datos: esqueleto mientras carga, error con reintento y estado vacío. */
export function ArtFrame({ query, height, empty, emptyKind = 'sin-ofertas', emptyTitle, emptyText, noProfileTitle, children }: Props) {
  if (query.isPending) {
    return (
      <div aria-busy="true" className="glass" style={{
        height,
        backgroundImage: 'radial-gradient(rgba(203,213,225,.10) 1px, transparent 1px)',
        backgroundSize: '18px 18px',
      }} />
    )
  }
  if (query.isError && noProfileTitle && query.error instanceof ApiError && query.error.status === 404) {
    return (
      <EmptyState kind="sin-perfil" title={noProfileTitle}>
        <Link to="/perfil" className="text-silver underline">Ir a Perfil</Link>
      </EmptyState>
    )
  }
  if (query.isError) {
    return (
      <div role="alert" className="glass flex flex-col items-center justify-center gap-3 p-6 text-sm" style={{ height }}>
        <p className="text-muted">{errorMessage(query.error)}</p>
        <button type="button" onClick={() => query.refetch()}
                className="rounded-lg border border-line px-3 py-1.5 text-silver hover:border-line-strong">
          Reintentar
        </button>
      </div>
    )
  }
  if (empty) return <EmptyState kind={emptyKind} title={emptyTitle} text={emptyText} />
  return <>{children}</>
}
