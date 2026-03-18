import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { DashboardPage, BrowserPage, DetailPage, OpportunitiesPage, QAPage, QAReviewPage } from './pages'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/browse" element={<BrowserPage />} />
          <Route path="/opportunities" element={<OpportunitiesPage />} />
          <Route path="/technology/:uuid" element={<DetailPage />} />
          <Route path="/qa" element={<QAPage />} />
          <Route path="/qa/:uuid" element={<QAReviewPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
