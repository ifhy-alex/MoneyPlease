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

  it('sin duplicados no muestra el aviso', () => {
    render(<JobCard job={job(1)} match={null} />)
    expect(screen.queryByText(/casi idéntica/)).toBeNull()
  })
})
