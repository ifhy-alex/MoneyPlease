import type { Insights } from '../api/types'

const fmt = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString('es-CR', { dateStyle: 'short', timeStyle: 'short' }) : 'nunca'

export function StatusStrip({ insights }: { insights: Insights }) {
  const { estado, punto_control } = insights
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
      <li>Última ingesta: {fmt(estado.ultima_ingesta)}</li>
      {estado.matching && (
        <li>
          Matching: {estado.matching.evaluadas} evaluadas
          {estado.matching.cuota_agotada && <span className="text-danger"> · cuota agotada</span>}
        </li>
      )}
      {estado.pendientes !== null && <li>Pendientes: {estado.pendientes}</li>}
      {estado.fuentes_con_error.length > 0 && (
        <li className="text-danger">Fuentes con error: {estado.fuentes_con_error.join(', ')}</li>
      )}
      <li className="text-text">
        Punto de control: <strong>{punto_control.relevantes}/10</strong> relevantes
      </li>
    </ul>
  )
}
