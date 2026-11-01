import { useEffect } from 'react'

export interface ToastState {
  message: string
  tone?: 'info' | 'error'
  action?: { label: string; onClick: () => void }
}

export function Toast({ toast, onClose, ms = 6000 }: { toast: ToastState | null; onClose: () => void; ms?: number }) {
  useEffect(() => {
    if (!toast) return
    const id = setTimeout(onClose, ms)
    return () => clearTimeout(id)
  }, [toast, onClose, ms])
  if (!toast) return null
  return (
    <div
      role={toast.tone === 'error' ? 'alert' : 'status'}
      className="fixed bottom-20 left-1/2 z-30 flex -translate-x-1/2 items-center gap-3 glass bg-bg/85 px-4 py-2 text-sm md:bottom-6"
    >
      <span className={toast.tone === 'error' ? 'text-danger' : ''}>{toast.message}</span>
      {toast.action && (
        <button type="button" className="font-medium text-accent" onClick={() => { toast.action!.onClick(); onClose() }}>
          {toast.action.label}
        </button>
      )}
    </div>
  )
}
