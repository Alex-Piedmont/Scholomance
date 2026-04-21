import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ErrorBoundary } from './components/ErrorBoundary'
import {
  DiscoveryPage,
  DashboardPage,
  BrowserPage,
  DetailPage,
  OpportunitiesPage,
  QAPage,
  QAReviewPage,
} from './pages'

function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<DiscoveryPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/browse" element={<BrowserPage />} />
            <Route path="/opportunities" element={<OpportunitiesPage />} />
            <Route path="/technology/:uuid" element={<DetailPage />} />
            <Route path="/qa" element={<QAPage />} />
            <Route path="/qa/:uuid" element={<QAReviewPage />} />
            <Route path="/qa/by-id/:dbId" element={<QAReviewPage />} />
          </Route>
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  )
}

export default App
