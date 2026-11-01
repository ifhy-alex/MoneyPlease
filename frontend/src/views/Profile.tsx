import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, errorMessage } from '../api/client'
import { useCreateApplication, useDraftFromCv, useFeedback, useProfile, useProfileVersions, useSaveProfile } from '../api/hooks'
import type { Perfil } from '../api/types'
import { JobDetail } from '../components/JobDetail'
import { errorsByField, ProfileForm } from '../components/ProfileForm'
import { Toast, type ToastState } from '../components/Toast'
import { EmptyState } from '../decor/EmptyState'

const Fingerprint = lazy(() => import('../art/Fingerprint'))
const SkillGraph = lazy(() => import('../art/SkillGraph'))

const EMPTY: Perfil = {
  skills: [], languages: [], experience_months: 0, seniority_target: ['practica', 'junior'], roles_target: [], summary: '',
  preferences: { modalidad: ['presencial', 'hibrido', 'remoto'], ubicaciones: ['Cartago', 'San José', 'Heredia', 'Alajuela'],
    remoto_abierto: true, excluir_titulo: [], excluir_palabras: [] },
}

export default function Profile() {
  const profile = useProfile()
  const versions = useProfileVersions()
  const save = useSaveProfile()
  const draft = useDraftFromCv()
  const [form, setForm] = useState<Perfil | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [notice, setNotice] = useState<{ text: string; tone: 'ok' | 'error' } | null>(null)
  const [sent, setSent] = useState<string | null>(null)
  const [open, setOpen] = useState<number | null>(null)
  const [toast, setToast] = useState<ToastState | null>(null)
  const closeToast = useCallback(() => setToast(null), [])
  const feedback = useFeedback()
  const createApp = useCreateApplication()
  const noProfile = profile.error instanceof ApiError && profile.error.status === 404

  useEffect(() => {
    if (profile.data && form === null) setForm(profile.data.perfil)
  }, [profile.data, form])

  const submit = (perfil: Perfil, label = 'Versión guardada') => {
    if (save.isPending) return
    setErrors({})
    save.mutate(perfil, {
      onSuccess: (v) => { setForm(v.perfil); setNotice({ text: `${label}: versión ${v.version}`, tone: 'ok' }) },
      onError: (err) => {
        if (err instanceof ApiError && err.status === 422) {
          setErrors(errorsByField(err.detail))
          setNotice({ text: 'Revisa los campos marcados', tone: 'error' })
        } else setNotice({ text: errorMessage(err), tone: 'error' })
      },
    })
  }

  const upload = (file: File | undefined) => {
    if (!file) return
    setNotice(null)
    draft.mutate(file, {
      onSuccess: (d) => { setForm(d.perfil); setSent(d.texto_enviado); setNotice({ text: 'Borrador cargado. Revísalo y guarda la versión.', tone: 'ok' }) },
      onError: (err) => setNotice({ text: errorMessage(err), tone: 'error' }),
    })
  }

  const value = form ?? (noProfile ? EMPTY : null)
  return (
    <div className="relative flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1>Tu perfil</h1>
          {profile.data && <p className="text-sm text-muted">Versión activa: {profile.data.version}</p>}
        </div>
        <label className="cursor-pointer rounded-lg border border-line px-3 py-2 text-sm hover:bg-surface">
          {draft.isPending ? 'Generando borrador…' : '⇪ Subir CV (PDF)'}
          <input type="file" accept="application/pdf" aria-label="Subir CV" className="sr-only"
                 disabled={draft.isPending} onChange={(e) => { upload(e.target.files?.[0]); e.target.value = '' }} />
        </label>
      </header>

      {noProfile && !form && (
        <EmptyState kind="sin-perfil" title="Todavía no tienes perfil guardado."
                    text="Sube tu CV para generar un borrador o llena el formulario." />
      )}
      {notice && (
        <p role={notice.tone === 'error' ? 'alert' : 'status'} className={notice.tone === 'error' ? 'text-danger' : 'text-ok'}>
          {notice.text}
        </p>
      )}
      {sent && (
        <details className="glass p-3 text-sm">
          <summary className="cursor-pointer">Texto enviado a Gemini (sin datos de contacto)</summary>
          <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap text-xs text-muted">{sent}</pre>
        </details>
      )}

      {value && (
        <form onSubmit={(e) => { e.preventDefault(); submit(value) }} className="flex flex-col gap-4">
          <ProfileForm value={value} onChange={setForm} errors={errors} />
          <button type="submit" disabled={save.isPending}
                  className="self-start rounded-lg bg-silver px-4 py-2 font-medium text-bg disabled:opacity-60">
            {save.isPending ? 'Guardando…' : 'Guardar versión'}
          </button>
        </form>
      )}

      {versions.data && versions.data.length > 0 && (
        <section className="grid gap-6 lg:grid-cols-[18rem_1fr]">
          <div className="flex flex-col gap-3">
            <h2>Huella e historial</h2>
            <Suspense fallback={null}><Fingerprint versions={versions.data} /></Suspense>
            <ol className="flex flex-col gap-2 text-sm">
              {versions.data.map((v) => (
                <li key={v.version} className="flex items-center justify-between gap-2">
                  <span>v{v.version} · {new Date(v.creado_en).toLocaleDateString('es-CR')}</span>
                  <span className="flex gap-2">
                    <button type="button" className="text-muted hover:text-text" onClick={() => setForm(v.perfil)}>Ver</button>
                    <button type="button" aria-label={`Restaurar versión ${v.version}`} className="text-accent"
                            disabled={save.isPending} onClick={() => submit(v.perfil, 'Restaurada')}>Restaurar</button>
                  </span>
                </li>
              ))}
            </ol>
          </div>
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between gap-2">
              <h2>Grafo de habilidades</h2>
              <Link to="/universo?vista=habilidades" className="mono rounded-lg border border-line px-2.5 py-1 text-[11px] text-silver hover:border-silver">
                Ver en 3D ↗
              </Link>
            </div>
            <p className="-mt-2 text-sm text-muted">Tus habilidades y las ofertas que las piden. Punteadas: las que piden y te faltan.</p>
            <Suspense fallback={null}><SkillGraph onOpen={setOpen} /></Suspense>
          </div>
        </section>
      )}
      {open !== null && (
        <JobDetail id={open} onClose={() => setOpen(null)}
                   onFeedback={(valor) => feedback.mutate({ jobId: open, valor }, { onError: (err) => setToast({ message: errorMessage(err), tone: 'error' }) })}
                   onSave={() => createApp.mutate(open, {
                     onSuccess: () => setToast({ message: 'Guardada en postulaciones' }),
                     onError: (err) => !(err instanceof ApiError && err.status === 409) && setToast({ message: errorMessage(err), tone: 'error' }),
                   })} />
      )}
      <Toast toast={toast} onClose={closeToast} />
    </div>
  )
}
