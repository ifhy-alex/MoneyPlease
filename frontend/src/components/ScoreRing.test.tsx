import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ScoreRing, scoreColor } from './ScoreRing'

describe('ScoreRing', () => {
  it.each([0, 55, 100])('renderiza score %i', (score) => {
    render(<ScoreRing score={score} fit="junior" />)
    expect(screen.getByRole('img', { name: new RegExp(`${score}`) })).toBeInTheDocument()
  })

  it('las prácticas usan trazo punteado', () => {
    const { container } = render(<ScoreRing score={80} fit="practica" />)
    expect(container.querySelector('[stroke-dasharray]')).not.toBeNull()
  })

  it('el color depende del score', () => {
    expect(scoreColor(30)).toBe('var(--danger)')
    expect(scoreColor(80)).toBe('var(--accent)')
  })
})
