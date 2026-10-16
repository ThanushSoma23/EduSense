import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { Navbar } from './components/Navbar'

import { LandingPage } from './pages/LandingPage'
import { TeacherDashboard } from './pages/TeacherDashboard'
import { ExamSetupPage } from './pages/ExamSetupPage'
import { UploadCenterPage } from './pages/UploadCenterPage'
import { ReviewWorkspacePage } from './pages/ReviewWorkspacePage'
import { PublishPage } from './pages/PublishPage'
import { StudentResultPage } from './pages/StudentResultPage'
import { AdminDashboard } from './pages/AdminDashboard'

export function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <div className="min-h-screen bg-[#FAF8F5] text-[#0F172A] flex flex-col font-sans">
          <Navbar />
          <main className="flex-1">
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/admin" element={<AdminDashboard />} />
              <Route path="/teacher/dashboard" element={<TeacherDashboard />} />
              <Route path="/teacher/exam/new" element={<ExamSetupPage />} />
              <Route path="/teacher/upload" element={<UploadCenterPage />} />
              <Route path="/teacher/review" element={<ReviewWorkspacePage />} />
              <Route path="/teacher/publish" element={<PublishPage />} />
              <Route path="/student/results" element={<StudentResultPage />} />
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
                boxShadow: '0 10px 30px -5px rgba(0, 0, 0, 0.1)'
              },
            }}
          />
        </div>
      </ThemeProvider>
    </AuthProvider>
  )
}

export default App
