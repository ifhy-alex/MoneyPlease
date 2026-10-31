import { DndContext, KeyboardSensor, PointerSensor, useDraggable, useDroppable, useSensor, useSensors, type DragEndEvent } from '@dnd-kit/core'
import type { ApplicationItem, Estado } from '../api/types'
import { CompanySeal } from './CompanySeal'

export const ESTADOS: { id: Estado; label: string }[] = [
  { id: 'guardada', label: 'Guardada' },
  { id: 'aplicada', label: 'Aplicada' },
  { id: 'entrevista', label: 'Entrevista' },
  { id: 'oferta', label: 'Oferta' },
  { id: 'rechazada', label: 'Rechazada' },
]

interface Props {
  apps: ApplicationItem[]
  onMove: (id: number, estado: Estado) => void
  onEdit: (app: ApplicationItem) => void
}

function Card({ app, onMove, onEdit }: { app: ApplicationItem } & Omit<Props, 'apps'>) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: app.id })
  const style = transform ? { transform: `translate(${transform.x}px, ${transform.y}px)` } : undefined
  return (
    <li ref={setNodeRef} style={style}
        className={`rounded-xl border border-line bg-surface p-3 text-sm shadow-sm ${isDragging ? 'opacity-70' : ''}`}>
      <div className="flex items-start gap-2">
        <span {...listeners} {...attributes} aria-label={`Arrastrar ${app.job.titulo}`} className="cursor-grab text-muted">⠿</span>
        <CompanySeal company={app.job.empresa} size={28} />
        <div className="min-w-0 flex-1">
          <p className="font-medium">{app.job.titulo}</p>
          <p className="text-xs text-muted">{app.job.empresa}</p>
          {app.seguimiento && <p className="mt-1 text-xs text-danger">Aplicaste hace {app.dias_en_estado} días</p>}
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between gap-2">
        {/* Alternativa accesible al arrastre: mover con el teclado o en pantallas táctiles. */}
        <label className="sr-only" htmlFor={`mover-${app.id}`}>Mover {app.job.titulo}</label>
        <select id={`mover-${app.id}`} value={app.estado} onChange={(e) => onMove(app.id, e.target.value as Estado)}
                className="rounded-md border border-line bg-bg px-1 py-0.5 text-xs">
          {ESTADOS.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
        <button type="button" onClick={() => onEdit(app)} aria-label={`Editar ${app.job.titulo}`}
                className="text-xs text-accent">Editar</button>
      </div>
    </li>
  )
}

function Column({ id, label, apps, onMove, onEdit }: { id: Estado; label: string } & Props) {
  const { setNodeRef, isOver } = useDroppable({ id })
  return (
    <section ref={setNodeRef} aria-label={`${label} (${apps.length})`}
             className={`flex min-w-56 flex-1 flex-col gap-2 rounded-[var(--radius-card)] border border-line p-3 ${isOver ? 'bg-surface' : ''}`}>
      <h2 className="text-base">{label} <span className="text-sm text-muted">{apps.length}</span></h2>
      <ul className="flex flex-col gap-2">
        {apps.map((a) => <Card key={a.id} app={a} onMove={onMove} onEdit={onEdit} />)}
      </ul>
    </section>
  )
}

export function Kanban({ apps, onMove, onEdit }: Props) {
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }), useSensor(KeyboardSensor))
  const onDragEnd = (e: DragEndEvent) => {
    const target = e.over?.id as Estado | undefined
    const app = apps.find((a) => a.id === e.active.id)
    if (app && target && target !== app.estado) onMove(app.id, target)
  }
  return (
    <DndContext sensors={sensors} onDragEnd={onDragEnd}>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {ESTADOS.map((s) => (
          <Column key={s.id} id={s.id} label={s.label} apps={apps.filter((a) => a.estado === s.id)}
                  onMove={onMove} onEdit={onEdit} />
        ))}
      </div>
    </DndContext>
  )
}
