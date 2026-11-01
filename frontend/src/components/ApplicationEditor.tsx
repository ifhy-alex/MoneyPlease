import { useState } from 'react'
import type { ApplicationChanges } from '../api/hooks'
import type { ApplicationItem, Estado } from '../api/types'
import { ConfirmDialog, Dialog } from './Dialog'
import { ESTADOS } from './Kanban'

interface Props {
  app: ApplicationItem
  onSave: (changes: ApplicationChanges) => void
  onDelete: () => void
  onClose: () => void
}

const field = 'rounded-lg border border-line bg-bg px-2 py-1.5 text-sm'

export function ApplicationEditor({ app, onSave, onDelete, onClose }: Props) {
  const [estado, setEstado] = useState<Estado>(app.estado)
  const [notas, setNotas] = useState(app.notas)
  const [fecha, setFecha] = useState(app.fecha_aplicacion ?? '')
  const [siguiente, setSiguiente] = useState(app.siguiente_paso)
  const [confirming, setConfirming] = useState(false)
  const save = () => {
    const changes: ApplicationChanges = { notas, siguiente_paso: siguiente, fecha_aplicacion: fecha || null }
    if (estado !== app.estado) changes.estado = estado
    onSave(changes)
  }
  return (
    <Dialog title={app.job.titulo} onClose={onClose}>
        <p className="-mt-2 text-sm text-muted">{app.job.empresa}</p>
        <label className="flex flex-col gap-1 text-sm">Estado
          <select value={estado} onChange={(e) => setEstado(e.target.value as Estado)} className={field}>
            {ESTADOS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">Fecha de aplicación
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className={field} />
        </label>
        <label className="flex flex-col gap-1 text-sm">Siguiente paso
          <input value={siguiente} onChange={(e) => setSiguiente(e.target.value)} className={field} />
        </label>
        <label className="flex flex-col gap-1 text-sm">Notas
          <textarea value={notas} onChange={(e) => setNotas(e.target.value)} rows={4} className={field} />
        </label>
        {app.estado === 'aplicada' && (
          <button type="button" className="self-start text-sm text-accent"
                  onClick={() => onSave({ recordatorio_hasta: new Date(Date.now() + 7 * 864e5).toISOString() })}>
            Posponer recordatorio 7 días
          </button>
        )}
        <div className="mt-2 flex justify-between">
          <button type="button" onClick={() => setConfirming(true)} className="text-sm text-danger">Eliminar</button>
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="rounded-lg px-3 py-1.5 text-sm text-muted">Cancelar</button>
            <button type="button" onClick={save} className="rounded-lg bg-silver px-3 py-1.5 text-sm font-medium text-bg">Guardar</button>
          </div>
        </div>
      {confirming && (
        <ConfirmDialog title="¿Borrar esta postulación?" text="Se pierden sus notas y su historial."
                       confirmLabel="Eliminar" onConfirm={onDelete} onCancel={() => setConfirming(false)} />
      )}
    </Dialog>
  )
}
