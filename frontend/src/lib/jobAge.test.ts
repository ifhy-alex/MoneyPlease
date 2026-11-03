import { describe, expect, it } from 'vitest'
import { job } from '../test/handlers'
import { jobAge } from './jobAge'

const NOW = new Date('2026-11-02T18:00:00-06:00')

describe('jobAge', () => {
  it('Workday y Lever dan la fecha de publicación', () => {
    const a = jobAge(job(1, { fuente: 'workday:hpe', publicado_en: '2026-10-30T10:00:00-06:00' }), NOW)
    expect(a.text).toBe('Publicada hace 3 días')
    expect(a.old).toBe(false)
    expect(a.iso).toBe('2026-10-30T10:00:00-06:00')
  })

  it('Greenhouse solo da la última actualización', () => {
    expect(jobAge(job(1, { fuente: 'greenhouse:gitlab', publicado_en: '2026-11-01T09:00:00-06:00' }), NOW).text)
      .toBe('Actualizada ayer')
  })

  it('las alertas de correo cuentan desde que llegaron', () => {
    expect(jobAge(job(1, { fuente: 'gmail', publicado_en: '2026-11-02T07:00:00-06:00' }), NOW).text)
      .toBe('Recibida hoy')
  })

  it('sin fecha de la fuente usa la primera vez que la vio la app', () => {
    expect(jobAge(job(1, { fuente: 'jsearch', publicado_en: null, primera_vez_visto: '2026-10-26T12:00:00-06:00' }),
                  NOW).text).toBe('Vista por primera vez hace 7 días')
  })

  it('cuenta días de calendario en Costa Rica, no bloques de 24 horas', () => {
    // 23:30 del día anterior en CR son menos de 24 h antes, pero ya es "ayer".
    expect(jobAge(job(1, { fuente: 'workday:hpe', publicado_en: '2026-11-01T23:30:00-06:00' }),
                  new Date('2026-11-02T08:00:00-06:00')).text).toBe('Publicada ayer')
  })

  it('pasado un mes habla en meses y marca la oferta como antigua', () => {
    const a = jobAge(job(1, { fuente: 'lever:toptal', publicado_en: '2026-08-20T12:00:00-06:00' }), NOW)
    expect(a.text).toBe('Publicada hace 2 meses')
    expect(a.old).toBe(true)
    expect(jobAge(job(1, { fuente: 'lever:toptal', publicado_en: '2026-10-01T12:00:00-06:00' }), NOW).text)
      .toBe('Publicada hace 1 mes')
  })

  it('más de un año', () => {
    expect(jobAge(job(1, { fuente: 'workday:hpe', publicado_en: '2025-06-01T12:00:00-06:00' }), NOW).text)
      .toBe('Publicada hace más de un año')
  })

  it('una fecha futura (reloj desfasado) cuenta como hoy', () => {
    expect(jobAge(job(1, { fuente: 'workday:hpe', publicado_en: '2026-11-03T12:00:00-06:00' }), NOW).text)
      .toBe('Publicada hoy')
  })
})
