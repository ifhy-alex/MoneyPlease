export type Fit = 'practica' | 'junior' | 'no_aplica'
export type Estado = 'guardada' | 'aplicada' | 'entrevista' | 'oferta' | 'rechazada'
export type Etiqueta = 'buena' | 'mala' | 'regular'
/** Dónde queda la oferta: en Costa Rica o remota desde el extranjero (regla en backend/moneyplease/scope.py). */
export type Ambito = 'cr' | 'internacional'
export type Area = 'backend' | 'frontend' | 'datos' | 'cloud' | 'testing' | 'idiomas'

export interface Job {
  id: number
  titulo: string
  empresa: string
  ubicacion: string
  modalidad: string
  pais: string | null
  url: string
  fuente: string
  ambito: Ambito
  publicado_en: string | null
  primera_vez_visto: string
}

export interface MatchInfo {
  score: number
  fit: Fit
  fortalezas: string[]
  brechas: string[]
  resumen: string
}

export interface TopItem {
  job: Job
  match: MatchInfo
  etiqueta: Etiqueta | null
  postulacion_id: number | null
  duplicados?: DuplicateRef[]
}

export interface ExploreItem {
  job: Job
  match: MatchInfo | null
  etiqueta: Etiqueta | null
  duplicados?: DuplicateRef[]
}

export interface ExplorePage {
  items: ExploreItem[]
  total: number
  page: number
}

export interface JobDetail {
  job: Job
  descripcion_texto: string
  match: MatchInfo | null
  etiqueta: Etiqueta | null
  postulacion: { id: number; estado: Estado } | null
  duplicados?: DuplicateRef[]
}

export interface Skill {
  name: string
  level: 'basico' | 'intermedio' | 'avanzado'
  evidence?: string | null
}

export interface Preferences {
  modalidad: ('presencial' | 'hibrido' | 'remoto')[]
  ubicaciones: string[]
  remoto_abierto: boolean
  excluir_titulo: string[]
  excluir_palabras: string[]
  /** Provincias donde se evalúan las ofertas de CR que no dicen su modalidad; los perfiles viejos no lo traen. */
  desconocida_en?: string[]
}

export interface Perfil {
  skills: Skill[]
  languages: { name: string; level: string }[]
  experience_months: number
  seniority_target: ('practica' | 'junior')[]
  roles_target: string[]
  summary: string
  preferences: Preferences
}

export interface ProfileVersion {
  version: number
  creado_en: string
  perfil: Perfil
  areas: Record<Area, number>
}

export interface Draft {
  perfil: Perfil
  texto_enviado: string
}

export interface ApplicationItem {
  id: number
  estado: Estado
  notas: string
  fecha_aplicacion: string | null
  siguiente_paso: string
  estado_desde: string
  recordatorio_hasta: string | null
  seguimiento: boolean
  dias_en_estado: number
  job: Job
  match: MatchInfo | null
}

export interface Insights {
  demo: boolean
  brechas_semana: { skill: string; n: number }[]
  estado: {
    ultima_ingesta: string | null
    fuentes_con_error: string[]
    matching: { fecha: string; candidatas: number; evaluadas: number; fallidas: number; cuota_agotada: boolean } | null
    pendientes: number | null
  }
  punto_control: { relevantes: number; etiquetadas: number }
  seguimiento: ApplicationItem[]
}

export interface SkillPoint {
  skill: string
  area: Area | 'otros'
  frecuencia: number
  tengo: boolean
  brecha: boolean
}

export interface DailyPoint {
  fecha: string
  nuevas: number
  score_promedio: number | null
}

export interface FlowPoint {
  semana: string
  fuente: string
  nuevas: number
}

export interface ExploreFilters {
  q?: string
  source?: string
  modalidad?: string
  ambito?: Ambito
  min_score?: number
  fit?: string
  desde?: string
  page?: number
  sort?: 'score' | 'fecha'
}

export interface MapPoint {
  job_id: number
  titulo: string
  empresa: string
  x: number
  y: number
  similitud: number
  puntaje: number | null
  etiqueta: Etiqueta | null
}

export interface MapData {
  total: number
  puntos: MapPoint[]
}

export interface GraphSkill {
  nombre: string
  nivel: string | null
  area: string
  grado: number
  tiene: boolean
}

export interface GraphOffer {
  job_id: number
  titulo: string
  empresa: string
  puntaje: number
}

export interface GraphEdge {
  habilidad: string
  job_id: number
}

export interface SkillsGraph {
  habilidades: GraphSkill[]
  ofertas: GraphOffer[]
  aristas: GraphEdge[]
}

export interface DuplicateRef {
  job_id: number
  url: string
}

export interface UniversePoint {
  job_id: number
  titulo: string
  empresa: string
  x: number
  y: number
  z: number
  similitud: number
  puntaje: number | null
  fit: Fit | null
  etiqueta: Etiqueta | null
  nube: number
  duplicados: number[]
}

export interface Nube {
  id: number
  nombre: string
  x: number
  y: number
  z: number
  n: number
}

export interface UniverseData {
  total: number
  puntos: UniversePoint[]
  nubes: Nube[]
}
