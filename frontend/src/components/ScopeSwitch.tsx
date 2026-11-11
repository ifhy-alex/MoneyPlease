import type { Ambito } from '../api/types'

const OPTIONS: [Ambito | undefined, string][] = [[undefined, 'Todas'], ['cr', 'Costa Rica'], ['internacional', 'Internacionales']]

/** Todas · Costa Rica · Internacionales. Un grupo de radios con forma de pastilla, navegable con el teclado. */
export function ScopeSwitch({ value, onChange }: { value: Ambito | undefined; onChange: (v: Ambito | undefined) => void }) {
  return (
    <div role="radiogroup" aria-label="Ámbito" className="inline-flex rounded-xl border border-line bg-surface p-0.5 text-sm">
      {OPTIONS.map(([v, label]) => (
        <label key={label}
               className={`cursor-pointer rounded-lg px-3 py-1 transition-colors has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-silver ${
                 value === v ? 'bg-surface-strong text-text' : 'text-muted hover:text-text'}`}>
          <input type="radio" name="ambito" className="sr-only" checked={value === v} onChange={() => onChange(v)} />
          {label}
        </label>
      ))}
    </div>
  )
}
