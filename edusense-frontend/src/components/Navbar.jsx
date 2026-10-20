import React, { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { GraduationCap, LogOut, ChevronDown, Sparkles, Menu, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export const Navbar = () => {
  const { user, role, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    setDropdownOpen(false)
    navigate('/')
  }

  const handleNavClick = (sectionId) => {
    setMobileMenuOpen(false)
    if (location.pathname === '/') {
      const el = document.getElementById(sectionId)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth' })
        return
      }
    }
    navigate(`/#${sectionId}`)
  }

  const handleOpenAuth = (mode) => {
    setMobileMenuOpen(false)
    if (location.pathname === '/') {
      window.dispatchEvent(new CustomEvent('edusense-auth-modal', { detail: { mode } }))
    } else {
      navigate(`/#${mode}`)
    }
  }

  return (
    <header className="sticky top-0 z-50 bg-[#FAF8F5]/90 backdrop-blur-md border-b border-[#EAE6DF] px-6 lg:px-12 py-3.5 flex items-center justify-between">
      {/* Brand Logo */}
      <Link to="/" className="flex items-center gap-3 group">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#FF5B35] to-[#FF8A48] p-0.5 shadow-md shadow-[#FF5B35]/20 group-hover:scale-105 transition-transform flex items-center justify-center">
          <GraduationCap className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-extrabold text-xl tracking-tight text-[#0F172A]">
              EduSense
            </span>
            <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
              MVP
            </span>
          </div>
          <p className="text-[11px] text-[#64748B] font-medium tracking-wide">
            AI-powered education
          </p>
        </div>
      </Link>

      {/* Center Public Navigation Links */}
      {!user && (
        <nav className="hidden md:flex items-center gap-8 text-sm font-semibold text-[#475569]">
          <button
            type="button"
            onClick={() => handleNavClick('features')}
            className="hover:text-[#FF5B35] transition-colors cursor-pointer"
          >
            Features
          </button>
          <button
            type="button"
            onClick={() => handleNavClick('how-it-works')}
            className="hover:text-[#FF5B35] transition-colors cursor-pointer"
          >
            How it works
          </button>
          <button
            type="button"
            onClick={() => handleNavClick('for-teachers-students')}
            className="hover:text-[#FF5B35] transition-colors cursor-pointer"
          >
            For teachers & students
          </button>
        </nav>
      )}

      {/* Nav Links for Authenticated Users */}
      {user && (
        <nav className="hidden md:flex items-center gap-1.5 bg-white p-1 rounded-xl border border-[#E2E8F0] shadow-sm">
          {role === 'admin' && (
            <Link
              to="/admin"
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                location.pathname === '/admin'
                  ? 'bg-[#FF5B35] text-white shadow-sm'
                  : 'text-[#475569] hover:text-[#0F172A] hover:bg-slate-50'
              }`}
            >
              Admin Approvals
            </Link>
          )}
          {role === 'teacher' && (
            <>
              <Link
                to="/teacher/dashboard"
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  location.pathname === '/teacher/dashboard'
                    ? 'bg-[#FF5B35] text-white shadow-sm'
                    : 'text-[#475569] hover:text-[#0F172A] hover:bg-slate-50'
                }`}
              >
                Dashboard
              </Link>
              <Link
                to="/teacher/exam/new"
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  location.pathname === '/teacher/exam/new'
                    ? 'bg-[#FF5B35] text-white shadow-sm'
                    : 'text-[#475569] hover:text-[#0F172A] hover:bg-slate-50'
                }`}
              >
                Setup Exam
              </Link>
              <Link
                to="/teacher/upload"
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  location.pathname === '/teacher/upload'
                    ? 'bg-[#FF5B35] text-white shadow-sm'
                    : 'text-[#475569] hover:text-[#0F172A] hover:bg-slate-50'
                }`}
              >
                Upload Sheets
              </Link>
              <Link
                to="/teacher/review"
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  location.pathname === '/teacher/review'
                    ? 'bg-[#FF5B35] text-white shadow-sm'
                    : 'text-[#475569] hover:text-[#0F172A] hover:bg-slate-50'
                }`}
              >
                Review Workspace
              </Link>
            </>
          )}
          {role === 'student' && (
            <Link
              to="/student/results"
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                location.pathname === '/student/results'
                  ? 'bg-[#FF5B35] text-white shadow-sm'
                  : 'text-[#475569] hover:text-[#0F172A] hover:bg-slate-50'
              }`}
            >
              Exams & Results
            </Link>
          )}
        </nav>
      )}

      {/* Right User Bar */}
      <div className="flex items-center gap-3">
        {user ? (
          /* Avatar Dropdown for Logged-In User */
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2.5 bg-white border border-[#E2E8F0] p-1.5 pr-3 rounded-2xl hover:border-[#FF5B35] transition-all shadow-sm cursor-pointer"
            >
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#FF5B35] to-[#FF8A48] text-white font-black flex items-center justify-center text-xs shadow-sm">
                {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="text-left hidden sm:block">
                <span className="block text-xs font-bold text-[#0F172A] leading-tight">
                  {user.full_name || 'User Profile'}
                </span>
                <span className="block text-[10px] text-[#FF5B35] capitalize font-semibold">
                  {user.role} {user.semester ? `(Sem ${user.semester} • Sec ${user.section || 1})` : ''}
                </span>
              </div>
              <ChevronDown className="w-4 h-4 text-[#94A3B8]" />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-64 bg-white rounded-2xl p-4 border border-[#E2E8F0] shadow-xl space-y-3 z-50">
                <div className="border-b border-[#F1F5F9] pb-3">
                  <p className="text-sm font-bold text-[#0F172A]">{user.full_name}</p>
                  <p className="text-xs text-[#64748B] truncate">{user.email}</p>
                  <span className="inline-block mt-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8] capitalize">
                    {user.role} Role
                  </span>
                </div>

                <button
                  onClick={handleLogout}
                  className="w-full py-2 px-3 rounded-xl bg-slate-100 hover:bg-rose-50 text-slate-700 hover:text-rose-600 font-bold text-xs flex items-center justify-center gap-2 transition-colors cursor-pointer"
                >
                  <LogOut className="w-4 h-4" />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        ) : (
          /* Public Top Navbar Buttons */
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => handleOpenAuth('login')}
              className="text-sm font-bold text-[#0F172A] hover:text-[#FF5B35] transition-colors cursor-pointer px-2 py-1"
            >
              Log in
            </button>
            <button
              type="button"
              onClick={() => handleOpenAuth('register')}
              className="px-4 sm:px-5 py-2.5 rounded-xl bg-[#FF5B35] hover:bg-[#E84E29] text-white font-bold text-xs shadow-md shadow-[#FF5B35]/25 hover:scale-105 transition-all flex items-center gap-1.5 cursor-pointer"
            >
              Get started free <span className="font-normal">→</span>
            </button>

            {/* Mobile Hamburger Button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="md:hidden p-2 text-slate-600 hover:text-[#FF5B35] transition-colors cursor-pointer"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        )}
      </div>

      {/* Mobile Drawer Menu */}
      {!user && mobileMenuOpen && (
        <div className="absolute top-full left-0 w-full bg-[#FAF8F5] border-b border-[#EAE6DF] p-6 shadow-xl space-y-4 md:hidden z-40 text-left">
          <button
            type="button"
            onClick={() => handleNavClick('features')}
            className="block w-full text-left font-bold text-sm text-[#0F172A] hover:text-[#FF5B35] py-2"
          >
            Features
          </button>
          <button
            type="button"
            onClick={() => handleNavClick('how-it-works')}
            className="block w-full text-left font-bold text-sm text-[#0F172A] hover:text-[#FF5B35] py-2"
          >
            How it works
          </button>
          <button
            type="button"
            onClick={() => handleNavClick('for-teachers-students')}
            className="block w-full text-left font-bold text-sm text-[#0F172A] hover:text-[#FF5B35] py-2"
          >
            For teachers & students
          </button>
          <div className="pt-2 border-t border-[#EAE6DF] flex flex-col gap-2">
            <button
              type="button"
              onClick={() => handleOpenAuth('login')}
              className="w-full py-2.5 text-center font-bold text-sm rounded-xl bg-white border border-[#CBD5E1] text-[#0F172A]"
            >
              Log in
            </button>
            <button
              type="button"
              onClick={() => handleOpenAuth('register')}
              className="w-full py-2.5 text-center font-bold text-sm rounded-xl bg-[#FF5B35] text-white"
            >
              Get started free
            </button>
          </div>
        </div>
      )}
    </header>
  )
}

export default Navbar
