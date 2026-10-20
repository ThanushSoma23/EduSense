import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  GraduationCap, Shield, User, ArrowRight, Sparkles, CheckCircle2,
  Building2, Eye, EyeOff, Lock, BarChart3, Clock, CheckCircle, Info,
  Brain, Scan, FileText, Award, Layers, ShieldCheck, ChevronRight
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

export const LandingPage = () => {
  const navigate = useNavigate()
  const { loginWithToken, user } = useAuth()

  // Modal / Auth view state
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [selectedRole, setSelectedRole] = useState('student') // 'student' | 'teacher'
  const [authMode, setAuthMode] = useState('register') // 'register' | 'login'

  // Password visibility
  const [showPassword, setShowPassword] = useState(false)

  // Colleges List from Backend
  const [colleges, setColleges] = useState([])

  // Shared Form Fields
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [collegeId, setCollegeId] = useState('')

  // Student-specific fields
  const [rollNumber, setRollNumber] = useState('')
  const [department, setDepartment] = useState('Computer Science')
  const [semester, setSemester] = useState(6)
  const [section, setSection] = useState(1)

  // Teacher-specific fields
  const [accessCode, setAccessCode] = useState('TEACH2026')

  // Error message state
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    fetchColleges()

    const handleAuthEvent = (e) => {
      if (e.detail?.mode) {
        setAuthMode(e.detail.mode)
      }
      setErrorMessage('')
      setShowAuthModal(true)
    }

    const handleHash = () => {
      const hash = window.location.hash
      if (hash === '#login') {
        setAuthMode('login')
        setErrorMessage('')
        setShowAuthModal(true)
      } else if (hash === '#register') {
        setAuthMode('register')
        setErrorMessage('')
        setShowAuthModal(true)
      } else if (hash) {
        const id = hash.replace('#', '')
        const el = document.getElementById(id)
        if (el) {
          setTimeout(() => el.scrollIntoView({ behavior: 'smooth' }), 100)
        }
      }
    }

    window.addEventListener('edusense-auth-modal', handleAuthEvent)
    window.addEventListener('hashchange', handleHash)
    handleHash()

    return () => {
      window.removeEventListener('edusense-auth-modal', handleAuthEvent)
      window.removeEventListener('hashchange', handleHash)
    }
  }, [])

  const fetchColleges = async () => {
    try {
      const res = await api.get('/auth/colleges')
      if (res.data?.colleges?.length) {
        setColleges(res.data.colleges)
        setCollegeId(res.data.colleges[0].id)
      } else {
        setColleges([
          { id: 'COLL-101', name: 'Indian Institute of Information Technology', code: 'IIIT' },
          { id: 'COLL-102', name: 'National Institute of Technology', code: 'NIT' }
        ])
        setCollegeId('COLL-101')
      }
    } catch (err) {
      setColleges([
        { id: 'COLL-101', name: 'Indian Institute of Information Technology', code: 'IIIT' }
      ])
      setCollegeId('COLL-101')
    }
  }

  const handleAuthSubmit = async (e) => {
    e.preventDefault()
    setErrorMessage('')

    try {
      if (authMode === 'register') {
        if (selectedRole === 'teacher') {
          const payload = {
            full_name: fullName,
            email,
            password,
            college_id: collegeId,
            access_code: accessCode,
            subjects: [{ subject: 'Data Structures & Algorithms', semester: 6 }]
          }
          const res = await api.post('/auth/register/teacher', payload)
          toast.success(res.data.message || 'Teacher registration submitted!')
          loginWithToken(res.data.token, res.data.user)

          if (res.data.user?.status === 'pending') {
            toast('Account submitted for admin approval.', { icon: '⏳' })
          } else {
            navigate('/teacher/dashboard')
          }
        } else {
          // Student Registration matching Kavya's mobile screenshot
          const payload = {
            full_name: fullName,
            email,
            roll_number: rollNumber,
            college_id: collegeId,
            department,
            semester: parseInt(semester, 10),
            section: parseInt(section, 10),
            password
          }
          const res = await api.post('/auth/register/student', payload)
          toast.success('Student account registered!')
          loginWithToken(res.data.token, res.data.user)
          navigate('/student/results')
        }
      } else {
        // Login Flow
        const payload = {
          email: email.includes('@') ? email : undefined,
          roll_number: !email.includes('@') ? email : undefined,
          college_id: collegeId,
          password
        }
        const res = await api.post('/auth/login', payload)
        toast.success(`Welcome back, ${res.data.user.full_name || res.data.user.name}!`)
        loginWithToken(res.data.token, res.data.user)

        if (res.data.user.role === 'admin') {
          navigate('/admin')
        } else if (res.data.user.role === 'teacher') {
          navigate('/teacher/dashboard')
        } else {
          navigate('/student/results')
        }
      }
      setShowAuthModal(false)
    } catch (err) {
      const msg = err.response?.data?.detail || 'Authentication failed. Please check inputs.'
      setErrorMessage(msg)
      toast.error(msg)
    }
  }

  return (
    <div className="relative min-h-[calc(100vh-69px)] bg-[#FAF8F5] flex flex-col justify-between overflow-x-hidden">
      <div className="max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 items-center px-6 lg:px-12 py-12 lg:py-16">
        
        {/* Left Column: Hero Copy matching Kavya's screenshot exactly */}
        <div className="lg:col-span-6 space-y-6 text-left">
          {/* Pill Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#EEF2FF] border border-[#E0E7FF] text-[#4F46E5] text-xs font-bold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" />
            AI-POWERED LEARNING & ASSESSMENT
          </div>

          {/* Heading */}
          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight leading-[1.08] text-[#0F172A]">
            Make every <br />
            assessment <br />
            <span className="text-[#FF5B35]">smarter.</span>
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg text-[#475569] max-w-xl leading-relaxed">
            Evaluate answers, manage exams, support students and turn feedback into better learning — all in one simple platform.
          </p>

          {/* CTAs */}
          <div className="flex flex-wrap items-center gap-4 pt-2">
            <button
              onClick={() => {
                setAuthMode('register')
                setShowAuthModal(true)
              }}
              className="px-6 py-3.5 rounded-xl bg-[#FF5B35] hover:bg-[#E84E29] text-white font-bold text-sm shadow-md shadow-[#FF5B35]/25 flex items-center gap-2 cursor-pointer transition-all hover:scale-105"
            >
              Get started free <ArrowRight className="w-4 h-4" />
            </button>

            <button
              type="button"
              onClick={() => {
                const el = document.getElementById('features')
                if (el) {
                  el.scrollIntoView({ behavior: 'smooth' })
                }
              }}
              className="px-6 py-3.5 rounded-xl bg-white border border-[#CBD5E1] text-[#0F172A] hover:bg-slate-50 font-bold text-sm shadow-sm cursor-pointer transition-all"
            >
              Explore EduSense
            </button>
          </div>

          {/* Trust Indicators */}
          <div className="flex flex-wrap items-center gap-6 pt-4 text-xs font-semibold text-[#64748B]">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#FF5B35]" />
              Teacher-controlled final marks
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#FF5B35]" />
              Secure role-based access
            </div>
          </div>
        </div>

        {/* Right Column: Teacher Dashboard Mockup Card matching Kavya's screenshot */}
        <div className="lg:col-span-6 relative">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="bg-white rounded-3xl p-6 sm:p-8 border border-[#E2E8F0] shadow-xl shadow-slate-200/50 space-y-6 relative text-left"
          >
            {/* Top Bar with Floating Pill */}
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-xl sm:text-2xl font-extrabold text-[#0F172A]">
                  Good morning, Teacher 👋
                </h3>
                <p className="text-xs text-[#64748B] mt-1">Here's what's happening today</p>
              </div>

              {/* Floating Pill from Screenshot */}
              <div className="bg-[#FAF8F5] border border-[#E2E8F0] px-3 py-1.5 rounded-xl shadow-sm flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <div>
                  <span className="text-[10px] font-bold text-[#64748B] uppercase block">Live overview</span>
                  <span className="text-xs font-bold text-[#0F172A]">82% <span className="text-[10px] text-emerald-600 font-semibold">+4.1%</span></span>
                </div>
              </div>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-[#FAF8F5] p-3.5 rounded-2xl border border-[#E2E8F0]/80">
                <span className="text-[11px] font-semibold text-[#64748B] block">Students</span>
                <span className="text-xl font-extrabold text-[#0F172A] block mt-1">248</span>
                <span className="text-[10px] text-emerald-600 font-bold">+12%</span>
              </div>
              <div className="bg-[#FAF8F5] p-3.5 rounded-2xl border border-[#E2E8F0]/80">
                <span className="text-[11px] font-semibold text-[#64748B] block">Evaluations</span>
                <span className="text-xl font-extrabold text-[#0F172A] block mt-1">86</span>
                <span className="text-[10px] text-[#FF5B35] font-bold">Today</span>
              </div>
              <div className="bg-[#FAF8F5] p-3.5 rounded-2xl border border-[#E2E8F0]/80">
                <span className="text-[11px] font-semibold text-[#64748B] block">Avg. score</span>
                <span className="text-xl font-extrabold text-[#0F172A] block mt-1">82%</span>
                <span className="text-[10px] text-emerald-600 font-bold">+3%</span>
              </div>
            </div>

            {/* Coral Bar Chart Activity */}
            <div className="space-y-2 pt-1">
              <div className="flex justify-between items-center text-xs">
                <span className="font-bold text-[#0F172A]">Evaluation activity</span>
                <span className="text-[11px] text-[#64748B]">This week</span>
              </div>
              <div className="h-28 flex items-end gap-2.5 pt-4 px-2 bg-[#FAF8F5] rounded-2xl border border-[#E2E8F0]">
                {[45, 60, 35, 75, 90, 80, 85].map((val, idx) => (
                  <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                    <div
                      className="w-full rounded-t-md bg-gradient-to-t from-[#FF5B35] to-[#FF8A48] transition-all hover:brightness-110"
                      style={{ height: `${val}%` }}
                    />
                    <span className="text-[9px] text-[#94A3B8] font-bold">
                      {['M', 'T', 'W', 'T', 'F', 'S', 'S'][idx]}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Floating Pill on bottom left from Screenshot */}
            <div className="p-3 bg-[#FFF0EB] rounded-2xl border border-[#FFD4C8] flex items-center gap-2.5 text-xs text-[#FF5B35] font-semibold">
              <Info className="w-4 h-4 shrink-0" />
              <span>AI evaluation: suggestions ready for teacher review</span>
            </div>
          </motion.div>
        </div>
      </div>

      {/* --- Section 1: Features (#features) --- */}
      <section id="features" className="w-full py-16 lg:py-24 border-t border-[#EAE6DF] bg-white/60">
        <div className="max-w-7xl mx-auto px-6 lg:px-12">
          <div className="text-center max-w-3xl mx-auto space-y-4 mb-14">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#FFF0EB] border border-[#FFD4C8] text-[#FF5B35] text-xs font-bold uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5" />
              INTELLIGENT PIPELINE ARCHITECTURE
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-[#0F172A] tracking-tight">
              Engineered for Academic Precision
            </h2>
            <p className="text-sm sm:text-base text-[#475569] leading-relaxed">
              A balanced hybrid evaluation pipeline uniting cutting-edge computer vision with teacher sovereignty.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="bg-white rounded-3xl p-8 border border-[#E2E8F0] shadow-sm hover:shadow-md transition-all space-y-4 flex flex-col justify-between">
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-[#FFF0EB] text-[#FF5B35] flex items-center justify-center font-bold">
                  <Scan className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-extrabold text-[#0F172A]">
                  Handwriting OCR & Preprocessing
                </h3>
                <p className="text-xs sm:text-sm text-[#475569] leading-relaxed">
                  Automated CLAHE contrast enhancement, deskewing, and segmentation with EasyOCR and TrOCR backends.
                </p>
              </div>
              <ul className="space-y-2 text-xs font-semibold text-[#64748B] pt-4 border-t border-[#F1F5F9]">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#FF5B35]" />
                  Adaptive contrast and binarization
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#FF5B35]" />
                  Question & answer segmentation
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#FF5B35]" />
                  Automatic low-confidence review flags
                </li>
              </ul>
            </div>

            {/* Feature 2 */}
            <div className="bg-white rounded-3xl p-8 border border-[#E2E8F0] shadow-sm hover:shadow-md transition-all space-y-4 flex flex-col justify-between">
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-[#EEF2FF] text-[#4F46E5] flex items-center justify-center font-bold">
                  <Brain className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-extrabold text-[#0F172A]">
                  Semantic Evaluation & Rubrics
                </h3>
                <p className="text-xs sm:text-sm text-[#475569] leading-relaxed">
                  Deep semantic similarity scoring and key concept extraction mapped directly to teacher rubrics.
                </p>
              </div>
              <ul className="space-y-2 text-xs font-semibold text-[#64748B] pt-4 border-t border-[#F1F5F9]">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#4F46E5]" />
                  Formula & diagram support
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#4F46E5]" />
                  Step-by-step concept scoring
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-[#4F46E5]" />
                  Strictly advisory recommendations
                </li>
              </ul>
            </div>

            {/* Feature 3 */}
            <div className="bg-white rounded-3xl p-8 border border-[#E2E8F0] shadow-sm hover:shadow-md transition-all space-y-4 flex flex-col justify-between">
              <div className="space-y-4">
                <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-extrabold text-[#0F172A]">
                  Teacher Sovereign Decision Point
                </h3>
                <p className="text-xs sm:text-sm text-[#475569] leading-relaxed">
                  AI suggestions never finalize grades. Educators retain full authority to override, adjust marks, and provide feedback.
                </p>
              </div>
              <ul className="space-y-2 text-xs font-semibold text-[#64748B] pt-4 border-t border-[#F1F5F9]">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Split-screen verification workspace
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Durable audit trail for overrides
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  One-click verified publication
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* --- Section 2: How It Works (#how-it-works) --- */}
      <section id="how-it-works" className="w-full py-16 lg:py-24 border-t border-[#EAE6DF] bg-[#FAF8F5]">
        <div className="max-w-7xl mx-auto px-6 lg:px-12">
          <div className="text-center max-w-3xl mx-auto space-y-4 mb-14">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#EEF2FF] border border-[#E0E7FF] text-[#4F46E5] text-xs font-bold uppercase tracking-wider">
              <Layers className="w-3.5 h-3.5" />
              STREAMLINED WORKFLOW
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-[#0F172A] tracking-tight">
              How EduSense Works
            </h2>
            <p className="text-sm sm:text-base text-[#475569] leading-relaxed">
              From rubric setup to student doubt resolution in four transparent, human-in-the-loop steps.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Step 1 */}
            <div className="bg-white rounded-2xl p-6 border border-[#E2E8F0] shadow-sm space-y-3 relative text-left">
              <span className="w-8 h-8 rounded-xl bg-[#FFF0EB] text-[#FF5B35] font-extrabold text-sm flex items-center justify-center">
                1
              </span>
              <h4 className="font-extrabold text-base text-[#0F172A]">Setup Exam & Rubric</h4>
              <p className="text-xs text-[#475569] leading-relaxed">
                Define questions, maximum marks, key concept criteria, and optional reference solutions or question photos.
              </p>
            </div>

            {/* Step 2 */}
            <div className="bg-white rounded-2xl p-6 border border-[#E2E8F0] shadow-sm space-y-3 relative text-left">
              <span className="w-8 h-8 rounded-xl bg-[#EEF2FF] text-[#4F46E5] font-extrabold text-sm flex items-center justify-center">
                2
              </span>
              <h4 className="font-extrabold text-base text-[#0F172A]">Upload Answer Sheets</h4>
              <p className="text-xs text-[#475569] leading-relaxed">
                Batch upload student handwritten copies with instant resolution, contrast, and orientation pre-validation.
              </p>
            </div>

            {/* Step 3 */}
            <div className="bg-white rounded-2xl p-6 border border-[#E2E8F0] shadow-sm space-y-3 relative text-left">
              <span className="w-8 h-8 rounded-xl bg-purple-50 text-purple-600 font-extrabold text-sm flex items-center justify-center">
                3
              </span>
              <h4 className="font-extrabold text-base text-[#0F172A]">AI Evaluates</h4>
              <p className="text-xs text-[#475569] leading-relaxed">
                AIML pipeline segments responses, computes concept coverage against rubrics, and suggests marks.
              </p>
            </div>

            {/* Step 4 */}
            <div className="bg-white rounded-2xl p-6 border border-[#E2E8F0] shadow-sm space-y-3 relative text-left">
              <span className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 font-extrabold text-sm flex items-center justify-center">
                4
              </span>
              <h4 className="font-extrabold text-base text-[#0F172A]">Teacher Approves & Publishes</h4>
              <p className="text-xs text-[#475569] leading-relaxed">
                Educators inspect scores, override where necessary, and publish official grades with instant student access.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* --- Section 3: For Teachers & Students (#for-teachers-students) --- */}
      <section id="for-teachers-students" className="w-full py-16 lg:py-24 border-t border-[#EAE6DF] bg-white/70">
        <div className="max-w-7xl mx-auto px-6 lg:px-12">
          <div className="text-center max-w-3xl mx-auto space-y-4 mb-14">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#FFF0EB] border border-[#FFD4C8] text-[#FF5B35] text-xs font-bold uppercase tracking-wider">
              <User className="w-3.5 h-3.5" />
              TAILORED EXPERIENCES
            </div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-[#0F172A] tracking-tight">
              Built for Teachers. Designed for Students.
            </h2>
            <p className="text-sm sm:text-base text-[#475569] leading-relaxed">
              Bridging the gap between efficient evaluation and personalized student feedback.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* For Teachers Card */}
            <div className="bg-[#FAF8F5] rounded-3xl p-8 border border-[#E2E8F0] shadow-sm space-y-6 flex flex-col justify-between text-left">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#FF5B35] text-white flex items-center justify-center font-bold">
                    <Shield className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-xl font-extrabold text-[#0F172A]">For Educators</h3>
                    <p className="text-xs text-[#64748B]">Grade faster while keeping 100% human oversight</p>
                  </div>
                </div>
                <ul className="space-y-3 text-xs sm:text-sm text-[#475569] pt-2">
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-[#FF5B35] shrink-0 mt-0.5" />
                    <span><strong>Cut evaluation turnaround time by 70%</strong> with automatic text extraction and concept alignment.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-[#FF5B35] shrink-0 mt-0.5" />
                    <span><strong>Eliminate repetitive rubric calculation</strong> across large batches of student exam scripts.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-[#FF5B35] shrink-0 mt-0.5" />
                    <span><strong>Sovereign control:</strong> Every mark is strictly advisory until you explicitly review and approve.</span>
                  </li>
                </ul>
              </div>
              <button
                type="button"
                onClick={() => {
                  setSelectedRole('teacher')
                  setAuthMode('register')
                  setShowAuthModal(true)
                }}
                className="w-full py-3.5 rounded-xl bg-[#0F172A] hover:bg-[#1E293B] text-white font-bold text-xs flex items-center justify-center gap-2 cursor-pointer transition-all"
              >
                Join as Teacher <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* For Students Card */}
            <div className="bg-[#FAF8F5] rounded-3xl p-8 border border-[#E2E8F0] shadow-sm space-y-6 flex flex-col justify-between text-left">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#4F46E5] text-white flex items-center justify-center font-bold">
                    <GraduationCap className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-xl font-extrabold text-[#0F172A]">For Students</h3>
                    <p className="text-xs text-[#64748B]">Understand your grades and master concepts</p>
                  </div>
                </div>
                <ul className="space-y-3 text-xs sm:text-sm text-[#475569] pt-2">
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-[#4F46E5] shrink-0 mt-0.5" />
                    <span><strong>Transparent concept breakdowns:</strong> See exactly which rubric criteria you fulfilled or missed.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-[#4F46E5] shrink-0 mt-0.5" />
                    <span><strong>AI Personal Tutor:</strong> Ask questions and get interactive explanations after your results are published.</span>
                  </li>
                  <li className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-[#4F46E5] shrink-0 mt-0.5" />
                    <span><strong>Email updates & secure portal:</strong> Get notified instantly when your instructor approves grades.</span>
                  </li>
                </ul>
              </div>
              <button
                type="button"
                onClick={() => {
                  setSelectedRole('student')
                  setAuthMode('login')
                  setShowAuthModal(true)
                }}
                className="w-full py-3.5 rounded-xl bg-[#FF5B35] hover:bg-[#E84E29] text-white font-bold text-xs flex items-center justify-center gap-2 cursor-pointer shadow-md shadow-[#FF5B35]/25 transition-all"
              >
                Access Student Portal <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* --- Footer --- */}
      <footer className="w-full py-10 border-t border-[#EAE6DF] bg-[#FAF8F5] text-left">
        <div className="max-w-7xl mx-auto px-6 lg:px-12 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#FF5B35] to-[#FF8A48] flex items-center justify-center text-white">
              <GraduationCap className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base text-[#0F172A]">EduSense</span>
                <span className="px-2 py-0.5 text-[9px] font-bold rounded-full bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
                  MVP
                </span>
              </div>
              <p className="text-[11px] text-[#64748B]">AI-powered academic assessment with human pedagogical authority.</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-xs font-semibold text-[#64748B]">
            <a href="#features" className="hover:text-[#FF5B35] transition-colors">Features</a>
            <a href="#how-it-works" className="hover:text-[#FF5B35] transition-colors">How it works</a>
            <a href="#for-teachers-students" className="hover:text-[#FF5B35] transition-colors">For teachers & students</a>
            <span>© 2026 EduSense AI</span>
          </div>
        </div>
      </footer>

      {/* Account Creation & Login Modal matching Kavya's mobile screenshot */}
      {showAuthModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-white rounded-3xl p-6 sm:p-8 max-w-md w-full border border-[#E2E8F0] shadow-2xl space-y-5 text-left relative"
          >
            {/* Header matching screenshot */}
            <div className="text-center space-y-1">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#FF5B35] to-[#FF8A48] text-white flex items-center justify-center mx-auto shadow-md shadow-[#FF5B35]/25">
                <GraduationCap className="w-6 h-6" />
              </div>
              <h3 className="text-2xl font-extrabold text-[#0F172A] pt-2">
                {authMode === 'register' ? 'Create your account' : 'Sign in to EduSense'}
              </h3>
              <p className="text-xs text-[#64748B]">
                {authMode === 'register' ? 'Register as a student or teacher.' : 'Access your evaluations and results'}
              </p>
            </div>

            {/* Student / Teacher Pill Switch matching screenshot */}
            <div className="grid grid-cols-2 gap-2 p-1 bg-[#F1F5F9] rounded-xl border border-[#E2E8F0]">
              <button
                type="button"
                onClick={() => setSelectedRole('student')}
                className={`py-2 rounded-lg font-bold text-xs flex items-center justify-center gap-2 transition-all ${
                  selectedRole === 'student'
                    ? 'bg-white text-[#FF5B35] shadow-sm'
                    : 'text-[#64748B] hover:text-[#0F172A]'
                }`}
              >
                <User className="w-3.5 h-3.5" />
                Student
              </button>
              <button
                type="button"
                onClick={() => setSelectedRole('teacher')}
                className={`py-2 rounded-lg font-bold text-xs flex items-center justify-center gap-2 transition-all ${
                  selectedRole === 'teacher'
                    ? 'bg-white text-[#FF5B35] shadow-sm'
                    : 'text-[#64748B] hover:text-[#0F172A]'
                }`}
              >
                <Shield className="w-3.5 h-3.5" />
                Teacher
              </button>
            </div>

            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold">
                {errorMessage}
              </div>
            )}

            <form onSubmit={handleAuthSubmit} className="space-y-3.5">
              {authMode === 'register' && (
                <div>
                  <label className="block text-xs font-bold text-[#0F172A] mb-1">Full name</label>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder={selectedRole === 'teacher' ? 'Prof. Sarah Jenkins' : 'Alex Rivera'}
                    className="w-full bg-[#FAF8F5] border border-[#CBD5E1] rounded-xl px-3.5 py-2.5 text-xs text-[#0F172A] focus:border-[#FF5B35] focus:outline-none"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-bold text-[#0F172A] mb-1">
                  {authMode === 'login' && selectedRole === 'student' ? 'Email or Roll number' : 'Email'}
                </label>
                <input
                  type="text"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={selectedRole === 'teacher' ? 'teacher@edusense.ai' : 'alex@edusense.ai'}
                  className="w-full bg-[#FAF8F5] border border-[#CBD5E1] rounded-xl px-3.5 py-2.5 text-xs text-[#0F172A] focus:border-[#FF5B35] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-[#0F172A] mb-1">Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full bg-[#FAF8F5] border border-[#CBD5E1] rounded-xl px-3.5 py-2.5 text-xs text-[#0F172A] focus:border-[#FF5B35] focus:outline-none pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-2.5 text-[#94A3B8] hover:text-[#0F172A]"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* College Selector matching screenshot */}
              <div>
                <label className="block text-xs font-bold text-[#0F172A] mb-1">College</label>
                <select
                  value={collegeId}
                  onChange={(e) => setCollegeId(e.target.value)}
                  className="w-full bg-[#FAF8F5] border border-[#CBD5E1] rounded-xl px-3 py-2.5 text-xs text-[#0F172A] focus:border-[#FF5B35] focus:outline-none"
                >
                  {colleges.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.code || c.id})
                    </option>
                  ))}
                </select>
                <span className="text-[10px] text-[#64748B] mt-0.5 block">Type or choose your college.</span>
              </div>

              {authMode === 'register' && selectedRole === 'student' && (
                <>
                  <div>
                    <label className="block text-xs font-bold text-[#0F172A] mb-1">Roll number</label>
                    <input
                      type="text"
                      required
                      value={rollNumber}
                      onChange={(e) => setRollNumber(e.target.value)}
                      placeholder="CS-2024-001"
                      className="w-full bg-[#FAF8F5] border border-[#CBD5E1] rounded-xl px-3.5 py-2.5 text-xs text-[#0F172A] focus:border-[#FF5B35] focus:outline-none"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-[#0F172A] mb-1">Semester</label>
                      <select
                        value={semester}
                        onChange={(e) => setSemester(Number(e.target.value))}
                        className="w-full bg-[#FAF8F5] border border-[#CBD5E1] rounded-xl px-3 py-2.5 text-xs text-[#0F172A] focus:border-[#FF5B35] focus:outline-none"
                      >
                        {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                          <option key={s} value={s}>
                            Semester {s}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-[#0F172A] mb-1">Section</label>
                      <select
                        value={section}
                        onChange={(e) => setSection(Number(e.target.value))}
                        className="w-full bg-[#FAF8F5] border border-[#CBD5E1] rounded-xl px-3 py-2.5 text-xs text-[#0F172A] focus:border-[#FF5B35] focus:outline-none"
                      >
                        {[1, 2, 3, 4].map((sec) => (
                          <option key={sec} value={sec}>
                            Section {sec}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </>
              )}

              {authMode === 'register' && selectedRole === 'teacher' && (
                <div>
                  <label className="block text-xs font-bold text-[#0F172A] mb-1">Access code</label>
                  <input
                    type="text"
                    required
                    value={accessCode}
                    onChange={(e) => setAccessCode(e.target.value)}
                    placeholder="TEACH2026"
                    className="w-full bg-[#FAF8F5] border border-[#CBD5E1] rounded-xl px-3.5 py-2.5 text-xs text-[#0F172A] focus:border-[#FF5B35] focus:outline-none"
                  />
                </div>
              )}

              <div className="pt-2 flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowAuthModal(false)}
                  className="flex-1 py-3 rounded-xl bg-slate-100 text-[#475569] font-bold text-xs hover:bg-slate-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 py-3 rounded-xl bg-[#FF5B35] hover:bg-[#E84E29] text-white font-bold text-xs shadow-md shadow-[#FF5B35]/25 transition-all"
                >
                  {authMode === 'register' ? 'Create account' : 'Sign in'}
                </button>
              </div>
            </form>

            <div className="text-center text-xs text-[#64748B] border-t border-[#F1F5F9] pt-3">
              {authMode === 'register' ? (
                <p>
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => {
                      setAuthMode('login')
                      setErrorMessage('')
                    }}
                    className="font-bold text-[#FF5B35] hover:underline"
                  >
                    Sign in here
                  </button>
                </p>
              ) : (
                <p>
                  Don't have an account?{' '}
                  <button
                    type="button"
                    onClick={() => {
                      setAuthMode('register')
                      setErrorMessage('')
                    }}
                    className="font-bold text-[#FF5B35] hover:underline"
                  >
                    Register here
                  </button>
                </p>
              )}
            </div>
          </motion.div>
        </div>
      )}

    </div>
  )
}

export default LandingPage
