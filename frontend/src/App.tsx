import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Grain } from './decor/Grain'
import { NightGradient } from './decor/NightGradient'

const Home = lazy(() => import('./views/Home'))
const Explore = lazy(() => import('./views/Explore'))
const Applications = lazy(() => import('./views/Applications'))
const Profile = lazy(() => import('./views/Profile'))

export default function App() {
  return (
    <Layout background={<><NightGradient /><Grain /></>}>
      <Suspense fallback={<p className="text-muted">Cargando…</p>}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/explorar" element={<Explore />} />
          <Route path="/postulaciones" element={<Applications />} />
          <Route path="/perfil" element={<Profile />} />
        </Routes>
      </Suspense>
    </Layout>
  )
}
