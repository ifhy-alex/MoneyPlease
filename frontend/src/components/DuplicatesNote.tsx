import type { DuplicateRef } from '../api/types'

/** Aviso de publicaciones casi idénticas (misma empresa, mismo texto) con un enlace a cada copia. */
export function DuplicatesNote({ duplicados }: { duplicados?: DuplicateRef[] }) {
  if (!duplicados?.length) return null
  const n = duplicados.length
  return (
    <p className="mono flex flex-wrap items-center gap-2 text-[11px] text-muted">
      <span>+{n} {n === 1 ? 'publicación casi idéntica' : 'publicaciones casi idénticas'}</span>
      {duplicados.map((d, i) => (
        <a key={d.job_id} href={d.url} target="_blank" rel="noreferrer noopener" className="text-silver hover:underline">
          ↗ {i + 2}
        </a>
      ))}
    </p>
  )
}
