// Mismos valores que theme.css: el test de contraste los verifica.
export const TOKENS = {
  dark: {
    bg: '#0b1020', surface: '#141a33', text: '#e8e6f0', muted: '#9a9cb8',
    accent: '#f2b84b', danger: '#ff7a6b', ok: '#7dd3a8',
  },
  light: {
    bg: '#f6f1e7', surface: '#fffaf0', text: '#1b1f33', muted: '#5b5f78',
    accent: '#b7791f', danger: '#c2410c', ok: '#2f855a',
  },
} as const

export type Theme = keyof typeof TOKENS
