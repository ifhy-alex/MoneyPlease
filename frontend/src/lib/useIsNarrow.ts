import { useEffect, useState } from 'react'

const QUERY = '(max-width: 639px)'

/** Pantalla angosta (celular): se actualiza al girar el dispositivo o cambiar el tamaño de la ventana. */
export function useIsNarrow(): boolean {
  const [narrow, setNarrow] = useState(() => window.matchMedia(QUERY).matches)
  useEffect(() => {
    const mq = window.matchMedia(QUERY)
    const onChange = () => setNarrow(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return narrow
}
