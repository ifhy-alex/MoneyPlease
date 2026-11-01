const fold = (s: string) => s.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().trim()

/** Búsqueda sin mayúsculas ni acentos; primero lo que empieza por el texto, luego lo que lo contiene. Máx. 8. */
export function search<T extends { id: string; text: string }>(q: string, items: T[]): T[] {
  const needle = fold(q)
  if (!needle) return []
  const starts: T[] = []
  const contains: T[] = []
  for (const item of items) {
    const hay = fold(item.text)
    if (hay.startsWith(needle)) starts.push(item)
    else if (hay.includes(needle)) contains.push(item)
  }
  return [...starts, ...contains].slice(0, 8)
}
