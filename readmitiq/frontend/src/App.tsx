import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Layout from './components/layout/Layout'
import DashboardPage from './pages/DashboardPage'
import PatientsPage from './pages/PatientsPage'
import PatientDetailPage from './pages/PatientDetailPage'
import PredictPage from './pages/PredictPage'
import ModelPage from './pages/ModelPage'
import FinancialsPage from './pages/FinancialsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#162030',
            color: '#e8f0fe',
            border: '1px solid #1e2f44',
            fontFamily: 'DM Sans, sans-serif',
            fontSize: '14px',
          },
        }}
      />
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard"        element={<DashboardPage />} />
          <Route path="patients"         element={<PatientsPage />} />
          <Route path="patients/:id"     element={<PatientDetailPage />} />
          <Route path="predict"          element={<PredictPage />} />
          <Route path="model"            element={<ModelPage />} />
          <Route path="financials"       element={<FinancialsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
