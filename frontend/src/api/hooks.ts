import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type {
  ApplicationItem, DailyPoint, Draft, Estado, Etiqueta, ExploreFilters, ExplorePage, FlowPoint, Insights, JobDetail,
  MapData, Perfil, ProfileVersion, SkillPoint, SkillsGraph, TopItem,
} from './types'

export type FeedbackValue = 'interesa' | 'no_interesa' | null
const LABEL: Record<'interesa' | 'no_interesa', Etiqueta> = { interesa: 'buena', no_interesa: 'mala' }

export const useInsights = () => useQuery({ queryKey: ['insights'], queryFn: () => api.get<Insights>('/insights') })
export const useTop = () => useQuery({ queryKey: ['top'], queryFn: () => api.get<TopItem[]>('/top') })
export const useJobs = (f: ExploreFilters) =>
  useQuery({ queryKey: ['jobs', f], queryFn: () => api.get<ExplorePage>('/jobs', { ...f }) })
export const useJob = (id: number | null) =>
  useQuery({ queryKey: ['job', id], queryFn: () => api.get<JobDetail>(`/jobs/${id}`), enabled: id !== null })
export const useMap = () => useQuery({ queryKey: ['map'], queryFn: () => api.get<MapData>('/map'), retry: false })
export const useSkillsGraph = () =>
  useQuery({ queryKey: ['skills-graph'], queryFn: () => api.get<SkillsGraph>('/skills-graph'), retry: false })
export const useSkills = () => useQuery({ queryKey: ['skills'], queryFn: () => api.get<SkillPoint[]>('/insights/skills') })
export const useDaily = () => useQuery({ queryKey: ['daily'], queryFn: () => api.get<DailyPoint[]>('/insights/daily') })
export const useFlow = () => useQuery({ queryKey: ['flow'], queryFn: () => api.get<FlowPoint[]>('/insights/flow') })

/** Etiqueta una oferta. Optimista sobre el top y Explorar; si el servidor falla, vuelve atrás. */
export function useFeedback() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ jobId, valor }: { jobId: number; valor: FeedbackValue }) =>
      api.post<void>(`/jobs/${jobId}/feedback`, { valor }),
    onMutate: async ({ jobId, valor }) => {
      await Promise.all([['top'], ['job', jobId], ['jobs']].map((queryKey) => qc.cancelQueries({ queryKey })))
      const previous = {
        top: qc.getQueryData<TopItem[]>(['top']),
        job: qc.getQueryData<JobDetail>(['job', jobId]),
        jobs: qc.getQueriesData<ExplorePage>({ queryKey: ['jobs'] }),
      }
      const etiqueta = valor ? LABEL[valor] : null
      qc.setQueryData<TopItem[]>(['top'], (items) =>
        items?.map((i) => (i.job.id === jobId ? { ...i, etiqueta } : i)))
      qc.setQueryData<JobDetail>(['job', jobId], (d) => (d ? { ...d, etiqueta } : d))
      qc.setQueriesData<ExplorePage>({ queryKey: ['jobs'] }, (page) =>
        page && { ...page, items: page.items.map((i) => (i.job.id === jobId ? { ...i, etiqueta } : i)) })
      return { previous, jobId }
    },
    onError: (_e, _v, ctx) => {
      if (!ctx) return
      qc.setQueryData(['top'], ctx.previous.top)
      qc.setQueryData(['job', ctx.jobId], ctx.previous.job)
      for (const [key, data] of ctx.previous.jobs) qc.setQueryData(key, data)
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['jobs'] })
      qc.invalidateQueries({ queryKey: ['job'] })
      qc.invalidateQueries({ queryKey: ['insights'] })
      qc.invalidateQueries({ queryKey: ['map'] })
      qc.invalidateQueries({ queryKey: ['skills-graph'] })
    },
  })
}

export const useApplications = () =>
  useQuery({ queryKey: ['applications'], queryFn: () => api.get<ApplicationItem[]>('/applications') })

export function useCreateApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: number) => api.post<ApplicationItem>('/applications', { job_id: jobId }),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['applications'] })
      qc.invalidateQueries({ queryKey: ['top'] })
      qc.invalidateQueries({ queryKey: ['job'] })
    },
  })
}

export interface ApplicationChanges {
  estado?: Estado
  notas?: string
  fecha_aplicacion?: string | null
  siguiente_paso?: string
  recordatorio_hasta?: string | null
}

/** Cambia una postulación. Optimista sobre la lista; si el servidor falla, vuelve atrás. */
export function useUpdateApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, changes }: { id: number; changes: ApplicationChanges }) =>
      api.patch<ApplicationItem>(`/applications/${id}`, changes),
    onMutate: async ({ id, changes }) => {
      await qc.cancelQueries({ queryKey: ['applications'] })
      const previous = qc.getQueryData<ApplicationItem[]>(['applications'])
      qc.setQueryData<ApplicationItem[]>(['applications'], (apps) =>
        apps?.map((a) => (a.id === id ? { ...a, ...changes } as ApplicationItem : a)))
      return { previous }
    },
    onError: (_e, _v, ctx) => ctx?.previous && qc.setQueryData(['applications'], ctx.previous),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['applications'] })
      qc.invalidateQueries({ queryKey: ['insights'] })
    },
  })
}

export function useDeleteApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.del<void>(`/applications/${id}`),
    onSettled: () => qc.invalidateQueries({ queryKey: ['applications'] }),
  })
}

export const useProfile = () =>
  useQuery({ queryKey: ['profile'], queryFn: () => api.get<ProfileVersion>('/profile'), retry: false })
export const useProfileVersions = () =>
  useQuery({ queryKey: ['profile-versions'], queryFn: () => api.get<ProfileVersion[]>('/profile/versions') })

export function useSaveProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (perfil: Perfil) => api.put<ProfileVersion>('/profile', perfil),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] })
      qc.invalidateQueries({ queryKey: ['profile-versions'] })
      qc.invalidateQueries({ queryKey: ['skills'] })
      // El perfil nuevo cambia el top, el mapa y el grafo: Inicio se refresca solo.
      for (const key of ['top', 'insights', 'map', 'skills-graph']) qc.invalidateQueries({ queryKey: [key] })
    },
  })
}

export function useDraftFromCv() {
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData()
      form.append('archivo', file)
      return api.post<Draft>('/profile/from-cv', form)
    },
  })
}
