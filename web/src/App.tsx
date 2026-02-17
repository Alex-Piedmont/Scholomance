import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { DashboardPage, BrowserPage, DetailPage, OpportunitiesPage } from './pages'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/browse" element={<BrowserPage />} />
          <Route path="/opportunities" element={<OpportunitiesPage />} />
          <Route path="/technology/:uuid" element={<DetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
