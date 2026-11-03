import { useState, type ReactNode } from 'react'
import type { Perfil, Skill } from '../api/types'

const PROVINCIAS = ['San José', 'Alajuela', 'Cartago', 'Heredia', 'Guanacaste', 'Puntarenas', 'Limón']
const MODALIDADES = [['presencial', 'Presencial'], ['hibrido', 'Híbrido'], ['remoto', 'Remoto']] as const
const NIVELES = [['basico', 'Básico'], ['intermedio', 'Intermedio'], ['avanzado', 'Avanzado']] as const
const field = 'rounded-lg border border-line bg-bg px-2 py-1.5 text-sm'

/** Errores del 422 de FastAPI agrupados por campo: ["body","preferences","modalidad",0] → "preferences.modalidad". */
export function errorsByField(detail: unknown): Record<string, string> {
  const out: Record<string, string> = {}
  if (!Array.isArray(detail)) return out
  for (const e of detail as { loc?: (string | number)[]; msg?: string }[]) {
    const key = (e.loc ?? []).filter((p) => p !== 'body' && typeof p === 'string').join('.')
    if (key && !out[key]) out[key] = e.msg ?? 'Valor inválido'
  }
  return out
}

function Group({ legend, error, children }: { legend: string; error?: string; children: ReactNode }) {
  return (
    <fieldset className="flex flex-col gap-2 rounded-[var(--radius-card)] border border-line p-4">
      <legend className="px-1 font-semibold text-base">{legend}</legend>
      {children}
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
    </fieldset>
  )
}

function ChipList({ label, values, onChange }: { label: string; values: string[]; onChange: (v: string[]) => void }) {
  const [draft, setDraft] = useState('')
  const add = () => {
    const v = draft.trim()
    if (v && !values.includes(v)) onChange([...values, v])
    setDraft('')
  }
  return (
    <div className="flex flex-col gap-2">
      <ul className="flex flex-wrap gap-1.5">
        {values.map((v) => (
          <li key={v} className="flex items-center gap-1 rounded-full bg-bg px-2 py-0.5 text-sm">
            {v}
            <button type="button" aria-label={`Quitar ${v}`} onClick={() => onChange(values.filter((x) => x !== v))}
                    className="text-muted hover:text-danger">×</button>
          </li>
        ))}
      </ul>
      <div className="flex gap-2">
        <input aria-label={`Agregar ${label}`} value={draft} onChange={(e) => setDraft(e.target.value)}
               onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add() } }} className={`${field} flex-1`} />
        <button type="button" onClick={add} className="rounded-lg border border-line px-3 text-sm">Agregar</button>
      </div>
    </div>
  )
}

function toggle<T>(list: T[], item: T, on: boolean): T[] {
  return on ? [...new Set([...list, item])] : list.filter((x) => x !== item)
}

export function ProfileForm({ value, onChange, errors }: { value: Perfil; onChange: (p: Perfil) => void; errors: Record<string, string> }) {
  const set = <K extends keyof Perfil>(k: K, v: Perfil[K]) => onChange({ ...value, [k]: v })
  const prefs = value.preferences
  const desconocida = prefs.desconocida_en ?? []
  const setPref = <K extends keyof Perfil['preferences']>(k: K, v: Perfil['preferences'][K]) =>
    onChange({ ...value, preferences: { ...prefs, [k]: v } })
  const [newSkill, setNewSkill] = useState('')
  const setSkill = (i: number, s: Skill) => set('skills', value.skills.map((x, j) => (j === i ? s : x)))

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Group legend="Habilidades" error={errors['skills']}>
        <ul className="flex flex-wrap gap-2">
          {value.skills.map((s, i) => (
            <li key={`${s.name}-${i}`} className="flex items-center gap-1 rounded-full bg-bg py-0.5 pl-3 pr-1 text-sm">
              {s.name}
              <select aria-label={`Nivel de ${s.name}`} value={s.level}
                      onChange={(e) => setSkill(i, { ...s, level: e.target.value as Skill['level'] })}
                      className="rounded-full bg-surface px-1 text-xs">
                {NIVELES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
              <button type="button" aria-label={`Quitar ${s.name}`} className="px-1 text-muted hover:text-danger"
                      onClick={() => set('skills', value.skills.filter((_, j) => j !== i))}>×</button>
            </li>
          ))}
        </ul>
        <div className="flex gap-2">
          <input aria-label="Nueva habilidad" value={newSkill} onChange={(e) => setNewSkill(e.target.value)} className={`${field} flex-1`} />
          <button type="button" className="rounded-lg border border-line px-3 text-sm" onClick={() => {
            if (newSkill.trim()) set('skills', [...value.skills, { name: newSkill.trim(), level: 'basico' }])
            setNewSkill('')
          }}>Agregar skill</button>
        </div>
      </Group>

      <Group legend="Resumen" error={errors['summary']}>
        <label className="sr-only" htmlFor="summary">Resumen</label>
        <textarea id="summary" rows={5} maxLength={600} value={value.summary}
                  onChange={(e) => set('summary', e.target.value)} className={field} />
        <p className="self-end text-xs text-muted">{value.summary.length}/600</p>
        <label className="flex items-center gap-2 text-sm">
          Meses de experiencia
          <input type="number" min={0} value={value.experience_months} className={`${field} w-24`}
                 onChange={(e) => set('experience_months', Number(e.target.value))} />
        </label>
        {errors['experience_months'] && <p role="alert" className="text-sm text-danger">{errors['experience_months']}</p>}
      </Group>

      <Group legend="Roles objetivo" error={errors['roles_target']}>
        <ChipList label="rol" values={value.roles_target} onChange={(v) => set('roles_target', v)} />
        <div className="flex gap-4 text-sm">
          {(['practica', 'junior'] as const).map((s) => (
            <label key={s} className="flex items-center gap-1">
              <input type="checkbox" checked={value.seniority_target.includes(s)}
                     onChange={(e) => set('seniority_target', toggle(value.seniority_target, s, e.target.checked))} />
              {s === 'practica' ? 'Práctica' : 'Junior'}
            </label>
          ))}
        </div>
        {errors['seniority_target'] && <p role="alert" className="text-sm text-danger">{errors['seniority_target']}</p>}
      </Group>

      <Group legend="Idiomas" error={errors['languages']}>
        {value.languages.map((l, i) => (
          <div key={i} className="flex gap-2">
            <input aria-label={`Idioma ${i + 1}`} value={l.name} className={`${field} flex-1`}
                   onChange={(e) => set('languages', value.languages.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} />
            <input aria-label={`Nivel del idioma ${i + 1}`} value={l.level} className={`${field} w-24`}
                   onChange={(e) => set('languages', value.languages.map((x, j) => (j === i ? { ...x, level: e.target.value } : x)))} />
            <button type="button" aria-label={`Quitar idioma ${i + 1}`} className="text-muted hover:text-danger"
                    onClick={() => set('languages', value.languages.filter((_, j) => j !== i))}>×</button>
          </div>
        ))}
        <button type="button" className="self-start text-sm text-accent"
                onClick={() => set('languages', [...value.languages, { name: '', level: '' }])}>+ Agregar idioma</button>
      </Group>

      <Group legend="Modalidad" error={errors['preferences.modalidad']}>
        <div className="flex gap-4 text-sm">
          {MODALIDADES.map(([v, l]) => (
            <label key={v} className="flex items-center gap-1">
              <input type="checkbox" checked={prefs.modalidad.includes(v)}
                     onChange={(e) => setPref('modalidad', toggle(prefs.modalidad, v, e.target.checked))} />
              {l}
            </label>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={prefs.remoto_abierto} onChange={(e) => setPref('remoto_abierto', e.target.checked)} />
          Aceptar ofertas remotas desde fuera de Costa Rica (LATAM, Anywhere…)
        </label>
      </Group>

      <Group legend="Provincias" error={errors['preferences.ubicaciones']}>
        <div className="grid grid-cols-2 gap-1 text-sm sm:grid-cols-4">
          {PROVINCIAS.map((p) => (
            <label key={p} className="flex items-center gap-1">
              <input type="checkbox" checked={prefs.ubicaciones.includes(p)}
                     onChange={(e) => setPref('ubicaciones', toggle(prefs.ubicaciones, p, e.target.checked))} />
              {p}
            </label>
          ))}
        </div>
      </Group>

      <Group legend="Sin modalidad indicada" error={errors['preferences.desconocida_en']}>
        <p className="text-xs text-muted">
          Muchas ofertas (sobre todo las alertas de correo) no dicen si son presenciales, híbridas o remotas.
          Se evalúan igual si están en estas provincias o en Costa Rica sin un lugar reconocido.
        </p>
        <div className="grid grid-cols-2 gap-1 text-sm sm:grid-cols-4">
          {PROVINCIAS.map((p) => (
            <label key={p} className="flex items-center gap-1">
              <input type="checkbox" checked={desconocida.includes(p)}
                     onChange={(e) => setPref('desconocida_en', toggle(desconocida, p, e.target.checked))} />
              {p}
            </label>
          ))}
        </div>
      </Group>

      <Group legend="Títulos a excluir" error={errors['preferences.excluir_titulo']}>
        <ChipList label="título a excluir" values={prefs.excluir_titulo} onChange={(v) => setPref('excluir_titulo', v)} />
      </Group>

      <Group legend="Palabras a excluir" error={errors['preferences.excluir_palabras']}>
        <ChipList label="palabra a excluir" values={prefs.excluir_palabras} onChange={(v) => setPref('excluir_palabras', v)} />
      </Group>
    </div>
  )
}
