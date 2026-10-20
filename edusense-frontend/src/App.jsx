import React from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuth } from './context/AuthContext'
import { Navbar } from './components/Navbar'

import { LandingPage } from './pages/LandingPage'
import { TeacherDashboard } from './pages/TeacherDashboard'
import { ExamSetupPage } from './pages/ExamSetupPage'
import { UploadCenterPage } from './pages/UploadCenterPage'
import { ReviewWorkspacePage } from './pages/ReviewWorkspacePage'
import { PublishPage } from './pages/PublishPage'
import { StudentResultPage } from './pages/StudentResultPage'
import { AdminDashboard } from './pages/AdminDashboard'

import Login from './pages/auth/Login'
import Register from './pages/auth/Register'

export function Protected({ children, roles }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FAF8F5] text-[#0F172A] font-semibold text-sm">
        Loading EduSense...
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to={`/${user.role || ''}`} replace />
  }

  return children
}

export function App() {
  return (
    <div className="min-h-screen bg-[#FAF8F5] text-[#0F172A] flex flex-col font-sans">
      <Navbar />
      <main className="flex-1">
        <Routes>
          {/* Public & Authentication Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Teacher Workflow Routes */}
          <Route
            path="/teacher/dashboard"
            element={
              <Protected roles={['teacher']}>
                <TeacherDashboard />
              </Protected>
            }
          />
          <Route
            path="/teacher/exam/new"
            element={
              <Protected roles={['teacher']}>
                <ExamSetupPage />
              </Protected>
            }
          />
          <Route
            path="/teacher/upload"
            element={
              <Protected roles={['teacher']}>
                <UploadCenterPage />
              </Protected>
            }
          />
          <Route
            path="/teacher/review"
            element={
              <Protected roles={['teacher']}>
                <ReviewWorkspacePage />
              </Protected>
            }
          />
          <Route
            path="/teacher/publish"
            element={
              <Protected roles={['teacher']}>
                <PublishPage />
              </Protected>
            }
          />

          {/* Teacher Navigation Aliases */}
          <Route path="/teacher" element={<Navigate to="/teacher/dashboard" replace />} />
          <Route path="/teacher/exams" element={<Navigate to="/teacher/dashboard" replace />} />
          <Route path="/teacher/evaluation" element={<Navigate to="/teacher/review" replace />} />
          <Route path="/teacher/knowledge" element={<Navigate to="/teacher/dashboard" replace />} />

          {/* Student Workflow Routes */}
          <Route
            path="/student/results"
            element={
              <Protected roles={['student']}>
                <StudentResultPage />
              </Protected>
            }
          />
          <Route path="/student" element={<Navigate to="/student/results" replace />} />
          <Route path="/student/tutor" element={<Navigate to="/student/results" replace />} />
          <Route path="/student/appeals" element={<Navigate to="/student/results" replace />} />

          {/* Admin Workflow Routes */}
          <Route
            path="/admin"
            element={
              <Protected roles={['admin']}>
                <AdminDashboard />
              </Protected>
            }
          />

          {/* Wildcard Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#FFFFFF',
            color: '#0F172A',
            border: '1px solid #E2E8F0',
            borderRadius: '12px',
            fontSize: '13px',
            fontWeight: '600',
            boxShadow: '0 10px 30px -5px rgba(0, 0, 0, 0.1)',
          },
        }}
      />
    </div>
  )
}

export default App
