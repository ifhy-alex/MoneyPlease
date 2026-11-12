import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { job } from '../test/handlers'
import { JobCard } from './JobCard'

describe('JobCard', () => {
  it('avisa de una publicación casi idéntica y enlaza a ella', () => {
    render(<JobCard job={job(1)} match={null} duplicados={[{ job_id: 2, url: 'https://hpe/1214221' }]} />)
    expect(screen.getByText(/\+1 publicación casi idéntica/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /↗ 2/ })).toHaveAttribute('href', 'https://hpe/1214221')
  })

  it('usa el plural con varias copias', () => {
    render(<JobCard job={job(1)} match={null}
                    duplicados={[{ job_id: 2, url: 'https://x/2' }, { job_id: 3, url: 'https://x/3' }]} />)
    expect(screen.getByText(/\+2 publicaciones casi idénticas/)).toBeInTheDocument()
  })

  it('muestra la antigüedad de la oferta con la fecha exacta', () => {
    render(<JobCard job={job(1, { fuente: 'workday:hpe', publicado_en: '2026-10-28T12:00:00-06:00' })} match={null} />)
    const age = screen.getByText(/^Publicada (hoy|ayer|hace .+)$/)
    expect(age.tagName).toBe('TIME')
    expect(age).toHaveAttribute('dateTime', '2026-10-28T12:00:00-06:00')
    expect(age).toHaveAttribute('title', expect.stringContaining('2026'))
  })

  it('una oferta de hace meses se marca como antigua', () => {
    render(<JobCard job={job(1, { fuente: 'workday:hpe', publicado_en: '2025-01-01T12:00:00-06:00' })} match={null} />)
    expect(screen.getByText(/más de un año/)).toHaveAttribute('title', expect.stringMatching(/puede que ya esté cerrada/))
  })

  it('las internacionales llevan su insignia y las de Costa Rica no', () => {
    const { rerender } = render(<JobCard job={job(1, { ambito: 'internacional' })} match={null} />)
    expect(screen.getByText(/internacional/i)).toBeInTheDocument()
    rerender(<JobCard job={job(1)} match={null} />)
    expect(screen.queryByText(/internacional/i)).toBeNull()
  })

  it('avisa cuando la evaluación se hizo solo con el título', () => {
    const { rerender } = render(<JobCard job={job(1, { solo_titulo: true })} match={null} />)
    const badge = screen.getByText(/solo título/i)
    expect(badge).toHaveAttribute('title', expect.stringMatching(/sin la descripción/i))
    rerender(<JobCard job={job(1)} match={null} />)
    expect(screen.queryByText(/solo título/i)).toBeNull()
  })

  it('sin duplicados no muestra el aviso', () => {
    render(<JobCard job={job(1)} match={null} />)
    expect(screen.queryByText(/casi idéntica/)).toBeNull()
  })
})
