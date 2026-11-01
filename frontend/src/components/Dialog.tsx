import { useEffect, useId, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
// Diálogos abiertos, el último arriba: Escape y Tab solo los atiende el de arriba (la confirmación sobre el editor).
const stack: symbol[] = []

interface Props {
  title: string
  onClose: () => void
  children: ReactNode
  variant?: 'center' | 'side'
  hideTitle?: boolean
}

/** Diálogo modal accesible: Escape cierra, el foco queda adentro y vuelve a donde estaba al cerrar. */
export function Dialog({ title, onClose, children, variant = 'center', hideTitle = false }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const titleId = useId()
  const close = useRef(onClose)
  close.current = onClose
  const id = useRef(Symbol('dialog'))

  useEffect(() => {
    const me = id.current
    stack.push(me)
    const previous = document.activeElement as HTMLElement | null
    const focusables = () => Array.from(ref.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? [])
    ;(focusables()[0] ?? ref.current)?.focus()

    const onKey = (e: KeyboardEvent) => {
      if (stack.at(-1) !== me) return
      if (e.key === 'Escape') {
        e.preventDefault()
        close.current()
      } else if (e.key === 'Tab') {
        const items = focusables()
        if (items.length === 0) return
        const first = items[0]
        const last = items[items.length - 1]
        const inside = ref.current?.contains(document.activeElement)
        if (e.shiftKey && (document.activeElement === first || !inside)) {
          e.preventDefault()
          last.focus()
        } else if (!e.shiftKey && (document.activeElement === last || !inside)) {
          e.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      stack.splice(stack.indexOf(me), 1)
      previous?.focus?.()
    }
  }, [])

  const panel = variant === 'side'
    ? 'fixed inset-y-0 right-0 flex w-full max-w-xl flex-col gap-4 overflow-y-auto border-l border-line bg-bg/85 p-6 backdrop-blur-xl'
    : 'glass panel flex w-full max-w-md flex-col gap-3 p-5'
  // En un portal: un diálogo dentro de otro panel con backdrop-filter quedaría recortado a ese panel.
  return createPortal(
    <div className={`fixed inset-0 z-30 bg-bg/60 ${variant === 'center' ? 'flex items-center justify-center p-4' : ''}`}
         onMouseDown={(e) => { if (e.target === e.currentTarget && stack.at(-1) === id.current) onClose() }}>
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} className={panel}>
        <h2 id={titleId} className={hideTitle ? 'sr-only' : 'text-xl'}>{title}</h2>
        {children}
      </div>
    </div>,
    document.body,
  )
}

interface ConfirmProps {
  title: string
  text?: string
  confirmLabel: string
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({ title, text, confirmLabel, onConfirm, onCancel }: ConfirmProps) {
  return (
    <Dialog title={title} onClose={onCancel}>
      {text && <p className="text-sm text-muted">{text}</p>}
      <div className="mt-2 flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="rounded-lg px-3 py-1.5 text-sm text-muted hover:text-text">
          Cancelar
        </button>
        <button type="button" onClick={onConfirm}
                className="rounded-lg border border-danger/60 bg-danger/15 px-3 py-1.5 text-sm font-medium text-danger">
          {confirmLabel}
        </button>
      </div>
    </Dialog>
  )
}
