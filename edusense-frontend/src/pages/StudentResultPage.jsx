import React, { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  Award, CheckCircle2, XCircle, Sparkles, BookOpen, BarChart3, Bot,
  Send, Loader2, RefreshCw, MessageSquare, ShieldCheck, ChevronRight,
  HelpCircle, ExternalLink, X, Layers, Search, Check, AlertTriangle,
  GraduationCap, Edit3, UserCheck, CheckCircle
} from 'lucide-react'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'
import { ScanViewer } from '../components/ScanViewer'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

export const StudentResultPage = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()

  // Query parameters
  const initialExamId = searchParams.get('exam_id') || '1'
  const submissionIdParam = searchParams.get('submission_id')
  const autoOpenTutor = searchParams.get('tutor') === 'true'
  const initialTab = searchParams.get('tab') || 'enrolled'

  // Portal Tab State: 'enrolled' | 'available' | 'results'
  const [activeTab, setActiveTab] = useState(initialTab)

  // Active Exam state for results view
  const [activeExamId, setActiveExamId] = useState(initialExamId)
  const [examTitle, setExamTitle] = useState('Official Exam Results')
  const [activeExamMeta, setActiveExamMeta] = useState(null)
  const [examResult, setExamResult] = useState(null)
  const [loadingResults, setLoadingResults] = useState(false)
  const [resultError, setResultError] = useState(null)
  const studentName = user?.full_name || 'Alex Rivera'
  const studentRoll = user?.roll_number || '22222222'
  const [selectedQuestionId, setSelectedQuestionId] = useState(null)
  const [questions, setQuestions] = useState([])

  // Enrollments and Available Exams State
  const [myEnrollments, setMyEnrollments] = useState([])
  const [loadingEnrollments, setLoadingEnrollments] = useState(true)

  const [availableExams, setAvailableExams] = useState([])
  const [loadingAvailable, setLoadingAvailable] = useState(false)
  const [filterSemester, setFilterSemester] = useState(user?.semester || 6)
  const [filterSection, setFilterSection] = useState(user?.section || 1)
  const [filterSubject, setFilterSubject] = useState('')
  const [subjectsCatalog, setSubjectsCatalog] = useState([])
  const [enrollingExamId, setEnrollingExamId] = useState(null)

  // Profile modal state
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [profileSemester, setProfileSemester] = useState(user?.semester || 6)
  const [profileSection, setProfileSection] = useState(user?.section || 1)
  const [savingProfile, setSavingProfile] = useState(false)

  // Tutor Chat Drawer / Modal State
  const [showTutorModal, setShowTutorModal] = useState(autoOpenTutor)
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [chatHistoryByQuestion, setChatHistoryByQuestion] = useState({})

  const getInitialWelcomeMessage = (q) => ({
    id: `welcome-${q?.id || 'default'}`,
    role: 'assistant',
    content: q
      ? `Hello! I am your AI Personal Tutor for Question ${q.number}: "${q.question_text?.slice(0, 90)}...". Ask me anything about your evaluated answer, model solutions, or how to master these concepts.`
      : 'Hello! I am your EduSense AI Personal Tutor. Ask me anything about your evaluated answers, model solutions, or how to master missed concepts.',
    provider: 'EduSense Tutor Core',
    citations: []
  })

  const chatEndRef = useRef(null)

  // Initialize and load subjects catalog & student data
  useEffect(() => {
    fetchMyEnrollments()
    fetchSubjects()
  }, [])

  // Sync user profile when user context updates
  useEffect(() => {
    if (user?.semester) {
      setFilterSemester(user.semester)
      setProfileSemester(user.semester)
    }
    if (user?.section) {
      setFilterSection(user.section)
      setProfileSection(user.section)
    }
  }, [user])

  // Load available exams when filters change or when switching to 'available' tab
  useEffect(() => {
    if (activeTab === 'available') {
      fetchAvailableExams()
    }
  }, [activeTab, filterSemester, filterSection, filterSubject])

  // Synchronize state with URL parameters
  useEffect(() => {
    const urlExamId = searchParams.get('exam_id')
    const urlTab = searchParams.get('tab')
    if (urlExamId && urlExamId !== activeExamId) {
      setActiveExamId(urlExamId)
    }
    if (urlTab && urlTab !== activeTab) {
      setActiveTab(urlTab)
    }
  }, [searchParams])

  // Fetch real exam results for results view
  useEffect(() => {
    if (activeExamId && activeTab === 'results') {
      fetchStudentResults(activeExamId)
    }
  }, [activeExamId, activeTab, submissionIdParam])

  useEffect(() => {
    if (autoOpenTutor) {
      setShowTutorModal(true)
    }
  }, [autoOpenTutor])

  useEffect(() => {
    setChatHistoryByQuestion({})
  }, [activeExamId])

  useEffect(() => {
    if (showTutorModal) {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [chatHistoryByQuestion, selectedQuestionId, showTutorModal])

  const fetchSubjects = async () => {
    try {
      const res = await api.get('/subjects')
      setSubjectsCatalog(Array.isArray(res.data) ? res.data : [])
    } catch (err) {
      console.warn('Could not load subjects catalog:', err)
    }
  }

  const fetchMyEnrollments = async () => {
    setLoadingEnrollments(true)
    try {
      const res = await api.get('/exams/student/my-enrollments')
      const list = Array.isArray(res.data) ? res.data : []
      setMyEnrollments(list)
    } catch (err) {
      console.warn('Could not load enrolled exams:', err)
    } finally {
      setLoadingEnrollments(false)
    }
  }

  const fetchAvailableExams = async () => {
    setLoadingAvailable(true)
    try {
      const params = {}
      if (filterSemester) params.semester = filterSemester
      if (filterSection) params.section = filterSection
      if (filterSubject) params.subject = filterSubject

      const res = await api.get('/exams/student/available', { params })
      setAvailableExams(Array.isArray(res.data) ? res.data : [])
    } catch (err) {
      console.error('Failed to load available exams:', err)
      toast.error('Failed to load available exams.')
    } finally {
      setLoadingAvailable(false)
    }
  }

  const handleSelfEnroll = async (examId) => {
    setEnrollingExamId(examId)
    try {
      const res = await api.post(`/exams/${examId}/self-enroll`)
      toast.success(res.data?.message || 'Successfully enrolled in exam!')
      fetchAvailableExams()
      fetchMyEnrollments()
    } catch (err) {
      console.error('Self enroll error:', err)
      const detail = err.response?.data?.detail || 'Failed to enroll in exam.'
      toast.error(detail)
    } finally {
      setEnrollingExamId(null)
    }
  }

  const handleSaveAcademicProfile = async (e) => {
    e.preventDefault()
    setSavingProfile(true)
    try {
      await api.put('/auth/me/academic-profile', {
        semester: parseInt(profileSemester, 10),
        section: parseInt(profileSection, 10)
      })
      toast.success('Academic profile updated successfully!')
      setShowProfileModal(false)
      setFilterSemester(profileSemester)
      setFilterSection(profileSection)
      if (refreshUser) refreshUser()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update academic profile.')
    } finally {
      setSavingProfile(false)
    }
  }

  const handleViewExamResults = (exam) => {
    const examIdStr = String(exam.id)
    setActiveExamId(examIdStr)
    setActiveExamMeta(exam)
    setSearchParams({ exam_id: examIdStr, tab: 'results' })
    setActiveTab('results')
    fetchStudentResults(examIdStr)
  }

  const fetchStudentResults = async (id) => {
    setLoadingResults(true)
    setResultError(null)
    try {
      let res
      if (submissionIdParam) {
        res = await api.get(`/final-marks/student/submissions/${submissionIdParam}`)
      } else {
        res = await api.get(`/final-marks/student/exam/${id}`)
      }

      if (res.data) {
        setExamResult(res.data)
        if (res.data.exam_title) {
          setExamTitle(`${res.data.exam_title} Official Results`)
        }
        if (res.data.questions?.length) {
          const mapped = res.data.questions.map((q) => ({
            id: q.question_id,
            number: q.question_number,
            name: `Q${q.question_number}`,
            question_text: q.question_text,
            awarded: q.final_approved_marks !== null && q.final_approved_marks !== undefined ? Number(q.final_approved_marks) : 0,
            max: Number(q.max_marks || 0),
            ai_suggested_marks: q.ai_suggested_marks,
            ai_feedback: q.ai_feedback,
            extracted_text: q.extracted_text,
            model_answer: q.model_answer,
            rubric: q.rubric,
            approval_status: q.approval_status,
            teacher_name: q.reviewing_teacher_name
          }))
          setQuestions(mapped)
          setSelectedQuestionId((prev) => (mapped.some((m) => m.id === prev) ? prev : mapped[0]?.id))
        }
      }
    } catch (err) {
      console.warn('Could not load student final marks:', err)
      const detail = err.response?.data?.detail || 'No published results available yet.'
      setResultError(detail)
      setExamResult(null)

      // Fallback: load tutor context so student can at least ask questions about the exam
      try {
        const ctxRes = await api.get(`/tutor/context/${id}`)
        if (ctxRes.data?.exam_title) {
          setExamTitle(`${ctxRes.data.exam_title} (Study Context)`)
        }
        if (ctxRes.data?.questions?.length) {
          const mapped = ctxRes.data.questions.map((q) => ({
            id: q.id,
            number: q.question_number,
            name: `Q${q.question_number}`,
            question_text: q.question_text,
            awarded: 0,
            max: Number(q.max_marks || 0),
            ai_feedback: 'Pending instructor evaluation.',
            extracted_text: null,
            model_answer: q.model_answer,
            rubric: q.rubric
          }))
          setQuestions(mapped)
          setSelectedQuestionId((prev) => (mapped.some((m) => m.id === prev) ? prev : mapped[0]?.id))
        }
      } catch (fallbackErr) {
        setQuestions([])
      }
    } finally {
      setLoadingResults(false)
    }
  }

  const currentQuestion = questions.find((q) => q.id === selectedQuestionId) || questions[0] || null
  const activeQuestionId = currentQuestion?.id
  const currentMessages = (activeQuestionId && chatHistoryByQuestion[activeQuestionId])
    ? chatHistoryByQuestion[activeQuestionId]
    : [getInitialWelcomeMessage(currentQuestion)]

  const chartData = questions.map((q) => ({
    name: `Q${q.number}`,
    fullName: q.question_text,
    Awarded: Number((q.awarded || 0).toFixed(1)),
    Max: Number((q.max || 0).toFixed(1)),
    question_id: q.id
  }))

  const totalAwarded = examResult?.total_final_marks !== null && examResult?.total_final_marks !== undefined
    ? Number(examResult.total_final_marks)
    : questions.reduce((sum, q) => sum + (q.awarded || 0), 0)

  const totalMax = examResult?.total_max_marks !== null && examResult?.total_max_marks !== undefined
    ? Number(examResult.total_max_marks)
    : questions.reduce((sum, q) => sum + (q.max || 0), 0)

  const percentage = totalMax > 0 ? ((totalAwarded / totalMax) * 100).toFixed(1) : '0.0'

  const handleSendMessage = async (customText = null, overrideQuestionId = null) => {
    const textToSend = customText || inputMessage
    if (!textToSend.trim() || isTyping) return

    const targetQ = (overrideQuestionId
      ? questions.find((q) => q.id === overrideQuestionId)
      : currentQuestion) || questions[0]
    const targetQId = targetQ?.id
    if (!targetQId) {
      toast.error('Please select a question to discuss with the AI Tutor.')
      return
    }

    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: textToSend.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    setChatHistoryByQuestion((prev) => {
      const existing = prev[targetQId] || [getInitialWelcomeMessage(targetQ)]
      return {
        ...prev,
        [targetQId]: [...existing, userMsg]
      }
    })

    if (!customText) setInputMessage('')
    setIsTyping(true)

    try {
      const res = await api.post('/tutor/chat', {
        exam_id: Number(activeExamId),
        question_id: targetQId,
        message: textToSend.trim(),
        submission_id: examResult?.submission_id || (submissionIdParam ? Number(submissionIdParam) : undefined)
      })

      const botReply = {
        id: `bot-${Date.now()}`,
        role: 'assistant',
        content: res.data.reply,
        provider: res.data.provider || 'EduSense Tutor AI',
        citations: res.data.citations || [],
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }

      setChatHistoryByQuestion((prev) => {
        const existing = prev[targetQId] || [getInitialWelcomeMessage(targetQ)]
        return {
          ...prev,
          [targetQId]: [...existing, botReply]
        }
      })
    } catch (err) {
      const detail = err.response?.data?.detail || 'Unable to reach AI Tutor. Please try again.'
      toast.error(detail)
      const errorReply = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${detail}`,
        provider: 'System Notice',
        citations: []
      }
      setChatHistoryByQuestion((prev) => {
        const existing = prev[targetQId] || [getInitialWelcomeMessage(targetQ)]
        return {
          ...prev,
          [targetQId]: [...existing, errorReply]
        }
      })
    } finally {
      setIsTyping(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8 text-left">
      {/* Top Banner: Student Identity & Academic Class */}
      <div className="bg-white p-6 md:p-8 rounded-3xl border border-slate-200/80 shadow-sm border-l-4 border-l-[#FF5B35] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8] inline-flex items-center gap-1.5">
              <GraduationCap className="w-3.5 h-3.5" />
              Student Academic Portal
            </span>
            <span className="text-xs text-slate-400">•</span>
            <span className="text-xs font-semibold text-slate-500 font-mono">
              Roll: {studentRoll}
            </span>
          </div>
          <h2 className="text-3xl font-extrabold font-display text-slate-900 mt-1">
            {studentName}
          </h2>
          <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-slate-600">
            <span>Enrolled Class:</span>
            <span className="px-2.5 py-0.5 rounded-full font-bold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
              Semester {user?.semester || 6}
            </span>
            <span className="px-2.5 py-0.5 rounded-full font-bold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
              Section {user?.section || 1}
            </span>
            <span className="px-2.5 py-0.5 rounded-full font-semibold bg-slate-100 text-slate-700 border border-slate-200">
              {user?.department || 'Computer Science'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowProfileModal(true)}
            className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-all flex items-center gap-2 border border-slate-200 cursor-pointer"
          >
            <Edit3 className="w-3.5 h-3.5 text-[#FF5B35]" />
            Update Class Info
          </button>
        </div>
      </div>

      {/* Main Tab Switcher */}
      <div className="flex items-center gap-2 bg-slate-100/80 p-1.5 rounded-2xl border border-slate-200 max-w-xl">
        <button
          type="button"
          onClick={() => {
            setActiveTab('enrolled')
            setSearchParams({ tab: 'enrolled' })
          }}
          className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer ${
            activeTab === 'enrolled'
              ? 'bg-white text-[#FF5B35] shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span>My Enrolled Exams</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-100 text-slate-700 font-mono">
            {myEnrollments.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => {
            setActiveTab('available')
            setSearchParams({ tab: 'available' })
          }}
          className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer ${
            activeTab === 'available'
              ? 'bg-white text-[#FF5B35] shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Search className="w-4 h-4" />
          <span>Enroll in Exams</span>
        </button>

        <button
          type="button"
          onClick={() => {
            setActiveTab('results')
            setSearchParams({ tab: 'results', exam_id: activeExamId })
          }}
          className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer ${
            activeTab === 'results'
              ? 'bg-white text-[#FF5B35] shadow-sm'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <Award className="w-4 h-4" />
          <span>Results & Tutor</span>
        </button>
      </div>

      {/* TAB 1: MY ENROLLED EXAMS */}
      {activeTab === 'enrolled' && (
        <div className="bg-white p-6 md:p-8 rounded-3xl border border-slate-200/80 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <h3 className="text-xl font-bold font-display text-slate-900">
                My Enrolled Courses & Exams
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Exams you are enrolled in. Evaluated submissions appear here for review once published by your teacher.
              </p>
            </div>
            <button
              type="button"
              onClick={fetchMyEnrollments}
              className="p-2 text-slate-400 hover:text-slate-600 transition-colors self-start sm:self-auto cursor-pointer"
              title="Refresh enrollments"
            >
              <RefreshCw className={`w-4 h-4 ${loadingEnrollments ? 'animate-spin text-[#FF5B35]' : ''}`} />
            </button>
          </div>

          {loadingEnrollments ? (
            <div className="py-12 flex items-center justify-center gap-2 text-sm text-slate-500">
              <RefreshCw className="w-4 h-4 animate-spin text-[#FF5B35]" />
              Loading your course enrollments...
            </div>
          ) : myEnrollments.length === 0 ? (
            <div className="py-12 text-center space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-orange-50 text-[#FF5B35] mx-auto flex items-center justify-center border border-orange-200">
                <BookOpen className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-base font-bold text-slate-800">You are not enrolled in any exams yet</h4>
                <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                  Browse exams matching your semester and section to self-enroll, or ask your course instructor for enrollment.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setActiveTab('available')}
                className="px-5 py-2.5 rounded-xl bg-[#FF5B35] text-white text-xs font-bold shadow-md shadow-[#FF5B35]/25 hover:scale-105 transition-all inline-flex items-center gap-2 cursor-pointer"
              >
                <Search className="w-4 h-4" /> Browse Available Exams
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {myEnrollments.map((ex) => {
                const isPublished = ex.status === 'PUBLISHED'
                return (
                  <div
                    key={ex.id}
                    className="p-5 rounded-2xl border border-slate-200 bg-white hover:border-slate-300 transition-all flex flex-col justify-between space-y-4 shadow-xs"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <span className="text-[11px] font-bold text-[#FF5B35] uppercase tracking-wider">
                          {ex.subject || 'Course'}
                        </span>
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                            isPublished
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                              : 'bg-amber-50 text-amber-800 border-amber-200'
                          }`}
                        >
                          {isPublished ? 'Results Published' : 'In Progress'}
                        </span>
                      </div>
                      <h4 className="text-base font-bold text-slate-900 line-clamp-1">{ex.title}</h4>
                      <p className="text-xs text-slate-500 font-mono mt-0.5">Code: {ex.code || `EX-${ex.id}`}</p>

                      <div className="flex flex-wrap items-center gap-1.5 mt-3">
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-extrabold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
                          Sem {ex.semester || '-'} • Sec {ex.section || '-'}
                        </span>
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-600">
                          Max: {ex.total_marks || 50} Marks
                        </span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                      <span className="text-[11px] text-slate-400">
                        {isPublished ? 'Official Marks Awarded' : 'Awaiting Teacher Review'}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleViewExamResults(ex)}
                        className="px-3.5 py-1.5 rounded-xl bg-[#FF5B35] hover:bg-[#E84E29] text-white font-bold text-xs shadow-sm transition-all flex items-center gap-1 cursor-pointer"
                      >
                        <Award className="w-3.5 h-3.5" />
                        View Performance
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: ENROLL IN AVAILABLE EXAMS */}
      {activeTab === 'available' && (
        <div className="bg-white p-6 md:p-8 rounded-3xl border border-slate-200/80 shadow-sm space-y-6">
          <div className="border-b border-slate-100 pb-4">
            <div className="flex items-center gap-2 text-xs font-bold text-[#FF5B35] uppercase tracking-wider mb-1">
              <Layers className="w-4 h-4" />
              <span>Course Enrollment Center</span>
            </div>
            <h3 className="text-xl font-bold font-display text-slate-900">
              Browse & Self-Enroll in Published Exams
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Filter by semester, section, and subject catalog. Only published exams open for your section are eligible for enrollment.
            </p>
          </div>

          {/* Academic Class Filters */}
          <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Semester Filter
              </label>
              <select
                value={filterSemester}
                onChange={(e) => setFilterSemester(Number(e.target.value))}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-[#FF5B35] focus:outline-none"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                  <option key={s} value={s}>
                    Semester {s} {user?.semester === s ? '(Your Semester)' : ''}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Section Filter
              </label>
              <select
                value={filterSection}
                onChange={(e) => setFilterSection(Number(e.target.value))}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-[#FF5B35] focus:outline-none"
              >
                {[1, 2, 3, 4].map((sec) => (
                  <option key={sec} value={sec}>
                    Section {sec} {user?.section === sec ? '(Your Section)' : ''}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Subject Filter
              </label>
              <select
                value={filterSubject}
                onChange={(e) => setFilterSubject(e.target.value)}
                className="w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:border-[#FF5B35] focus:outline-none"
              >
                <option value="">All Subjects</option>
                {subjectsCatalog.map((sub) => (
                  <option key={sub.id || sub.name} value={sub.name}>
                    {sub.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Available Exams Listing */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                Available Courses for Semester {filterSemester} • Section {filterSection}
                <span className="text-xs text-slate-400 font-normal">
                  ({availableExams.length} match{availableExams.length !== 1 ? 'es' : ''})
                </span>
              </h4>
              <button
                type="button"
                onClick={fetchAvailableExams}
                className="text-xs font-bold text-[#FF5B35] hover:underline flex items-center gap-1 cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingAvailable ? 'animate-spin' : ''}`} />
                Refresh List
              </button>
            </div>

            {loadingAvailable ? (
              <div className="py-12 flex items-center justify-center gap-2 text-sm text-slate-500">
                <RefreshCw className="w-4 h-4 animate-spin text-[#FF5B35]" />
                Searching available exams...
              </div>
            ) : availableExams.length === 0 ? (
              <div className="p-6 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-2">
                <p className="text-sm font-bold text-slate-700">No published exams found for this class</p>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  There are no published exams currently scheduled for Semester {filterSemester}, Section {filterSection}
                  {filterSubject ? ` under ${filterSubject}` : ''}.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {availableExams.map((ex) => {
                  const isEnrolled = !!ex.is_enrolled
                  const isPublished = ex.status === 'PUBLISHED'
                  const isClassMatch =
                    (!ex.semester || ex.semester === (user?.semester || 6)) &&
                    (!ex.section || ex.section === (user?.section || 1))

                  return (
                    <div
                      key={ex.id}
                      className={`p-5 rounded-2xl border transition-all flex flex-col justify-between space-y-4 ${
                        isEnrolled
                          ? 'bg-emerald-50/40 border-emerald-200'
                          : 'bg-white border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div>
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <span className="text-[11px] font-bold text-[#FF5B35] uppercase tracking-wider">
                            {ex.subject || 'Course'}
                          </span>
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
                            Sem {ex.semester || '-'} • Sec {ex.section || '-'}
                          </span>
                        </div>
                        <h4 className="text-base font-bold text-slate-900">{ex.title}</h4>
                        <div className="flex items-center gap-3 text-xs text-slate-500 mt-1 font-mono">
                          <span>Code: {ex.code || `EX-${ex.id}`}</span>
                          <span>•</span>
                          <span>Max Marks: {ex.total_marks || 50}</span>
                        </div>

                        {!isClassMatch && (
                          <div className="mt-2.5 p-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-[11px] flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-600" />
                            <span>
                              Class mismatch: Your profile is Sem {user?.semester || 6} Sec {user?.section || 1}.
                            </span>
                          </div>
                        )}
                      </div>

                      <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                        <div>
                          {isEnrolled ? (
                            <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-100 px-2.5 py-1 rounded-lg">
                              <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                              Enrolled
                            </span>
                          ) : (
                            <span className="text-xs text-slate-400">
                              {isPublished ? 'Open for enrollment' : 'Draft / Closed'}
                            </span>
                          )}
                        </div>

                        {isEnrolled ? (
                          <button
                            type="button"
                            onClick={() => handleViewExamResults(ex)}
                            className="px-3.5 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold transition-all cursor-pointer"
                          >
                            Go to Performance →
                          </button>
                        ) : (
                          <button
                            type="button"
                            disabled={enrollingExamId === ex.id || !isPublished}
                            onClick={() => handleSelfEnroll(ex.id)}
                            className="px-4 py-2 rounded-xl bg-[#FF5B35] hover:bg-[#E84E29] disabled:opacity-50 text-white font-bold text-xs shadow-md shadow-[#FF5B35]/25 transition-all flex items-center gap-1.5 cursor-pointer"
                          >
                            <UserCheck className="w-3.5 h-3.5" />
                            {enrollingExamId === ex.id ? 'Enrolling...' : 'Enroll Now'}
                          </button>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: PERFORMANCE SCRIPT, RECHARTS, & AI PERSONAL TUTOR */}
      {activeTab === 'results' && (
        <div className="space-y-8">
          {/* Header Banner */}
          <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm border-l-4 border-l-[#FF5B35] flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-orange-50 text-[#FF5B35] border border-orange-200 inline-flex items-center gap-1.5">
                <Sparkles className="w-3 h-3" />
                {examTitle}
              </span>
              <h2 className="text-3xl font-extrabold font-display text-slate-900 mt-2">
                Student Performance Script
              </h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Candidate: <strong className="text-slate-800">{studentName}</strong> (ID: {studentRoll})
              </p>
            </div>

            <div className="bg-orange-50/50 p-4 rounded-2xl border border-orange-200/80 text-center min-w-[200px]">
              <span className="text-xs font-bold text-slate-500 uppercase">Final Total Score</span>
              <div className="text-3xl font-extrabold text-[#FF5B35] font-display">
                {totalAwarded.toFixed(1)} <span className="text-base text-slate-400">/ {totalMax.toFixed(1)}</span>
              </div>
              <span className="text-xs text-emerald-700 font-bold">
                {percentage}% — {Number(percentage) >= 75 ? 'Grade A (Distinction)' : Number(percentage) >= 50 ? 'Grade B (Proficient)' : 'Passing Grade'}
              </span>
            </div>
          </div>

          {loadingResults ? (
            <div className="bg-white p-12 rounded-3xl border border-slate-200 text-center space-y-3">
              <Loader2 className="w-8 h-8 animate-spin text-[#FF5B35] mx-auto" />
              <p className="text-sm font-bold text-slate-700">Loading student evaluation and answer sheet...</p>
            </div>
          ) : resultError && !examResult ? (
            <div className="bg-amber-50/70 p-6 rounded-3xl border border-amber-200 text-amber-900 space-y-3">
              <div className="flex items-center gap-2 font-bold text-base">
                <AlertTriangle className="w-5 h-5 text-amber-600" />
                Results Pending Publication
              </div>
              <p className="text-xs text-amber-800">
                {resultError}
              </p>
              <p className="text-xs text-slate-600">
                Once your course instructor verifies evaluations and publishes the exam, your official marks and reviewed answer sheet will appear here.
              </p>
            </div>
          ) : (
            <>
              {/* Recharts Score Breakdown Chart */}
              <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold font-display text-slate-900 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-[#FF5B35]" />
                    Per-Question Score Breakdown
                  </h3>
                  <span className="text-xs text-slate-400">
                    Click any question bar to view details
                  </span>
                </div>

                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={chartData}
                      onClick={(state) => {
                        if (state && state.activePayload && state.activePayload.length > 0) {
                          const clickedQId = state.activePayload[0].payload.question_id
                          if (clickedQId) setSelectedQuestionId(clickedQId)
                        }
                      }}
                      className="cursor-pointer"
                    >
                      <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                      <YAxis stroke="#94a3b8" fontSize={12} domain={[0, Math.max(...questions.map((q) => q.max), 5)]} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '12px', color: '#0f172a' }}
                        formatter={(val, name) => [`${val} Marks`, name === 'Awarded' ? 'Approved Final Marks' : 'Maximum Marks']}
                        labelFormatter={(label, items) => {
                          const item = items?.[0]?.payload
                          return item?.fullName ? `${label}: ${item.fullName}` : label
                        }}
                      />
                      <Bar dataKey="Awarded" fill="#FF5B35" radius={[8, 8, 0, 0]} />
                      <Bar dataKey="Max" fill="#e2e8f0" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Question Navigation Selector Pills */}
              {questions.length > 0 && (
                <div className="flex items-center gap-2 overflow-x-auto pb-1">
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider shrink-0 mr-1">
                    Select Question:
                  </span>
                  {questions.map((q) => {
                    const isSelected = (currentQuestion?.id === q.id)
                    return (
                      <button
                        key={q.id}
                        type="button"
                        onClick={() => setSelectedQuestionId(q.id)}
                        className={`px-4 py-2 rounded-2xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer border ${
                          isSelected
                            ? 'bg-[#FF5B35] text-white border-[#FF5B35] shadow-md shadow-[#FF5B35]/25'
                            : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200'
                        }`}
                      >
                        <span>Question {q.number}</span>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold ${
                          isSelected ? 'bg-white/25 text-white' : 'bg-slate-100 text-slate-600'
                        }`}>
                          {q.awarded.toFixed(1)} / {q.max.toFixed(1)}
                        </span>
                      </button>
                    )
                  })}
                </div>
              )}

              {/* Scanned Viewer & Concept Breakdown */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-6 h-[560px]">
                  <ScanViewer
                    studentName={studentName}
                    questionNumber={currentQuestion?.number || 1}
                    fileUrl={examResult?.file_url}
                    fileName={examResult?.file_reference}
                    fileType={examResult?.file_reference?.toLowerCase().endsWith('.pdf') ? 'pdf' : 'image'}
                  />
                </div>

                <div className="lg:col-span-6 bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm space-y-5 flex flex-col justify-between">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-bold font-display text-slate-900 flex items-center gap-2">
                        <Award className="w-5 h-5 text-[#FF5B35]" />
                        Teacher Evaluation & Remarks
                      </h3>
                      <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200 inline-flex items-center gap-1">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        {currentQuestion?.approval_status === 'APPROVED' ? 'Teacher Approved' : 'Teacher Reviewed'}
                      </span>
                    </div>

                    {/* Question Card */}
                    <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
                      <div className="flex justify-between items-center text-xs font-bold text-slate-800">
                        <span className="text-sm font-bold text-slate-900">
                          Question {currentQuestion?.number || 1}
                        </span>
                        <span className="text-[#FF5B35] text-sm font-extrabold font-mono">
                          Awarded: {(currentQuestion?.awarded ?? 0).toFixed(1)} / {(currentQuestion?.max ?? 0).toFixed(1)}
                        </span>
                      </div>
                      <p className="text-xs text-slate-700 leading-relaxed font-medium">
                        {currentQuestion?.question_text || 'No question prompt available.'}
                      </p>
                    </div>

                    {/* Evaluator Remarks */}
                    <div className="space-y-2 pt-1">
                      <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        Evaluator Remarks
                      </h4>
                      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 leading-relaxed">
                        {currentQuestion?.ai_feedback || 'Evaluation completed. Marks have been approved by the teacher.'}
                      </div>
                    </div>

                    {/* Student Extracted Transcript Snippet (if available) */}
                    {currentQuestion?.extracted_text && (
                      <div className="space-y-2 pt-1">
                        <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                          <Layers className="w-3.5 h-3.5 text-[#FF5B35]" />
                          Your Transcribed Answer
                        </h4>
                        <div className="p-3 rounded-xl bg-amber-50/50 border border-amber-200/60 text-xs text-slate-800 font-mono max-h-28 overflow-y-auto whitespace-pre-wrap">
                          {currentQuestion.extracted_text}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Functional AI Personal Tutor Card */}
                  <div className="p-5 rounded-2xl bg-gradient-to-br from-[#FFF5F2] to-[#FAF8F5] border border-[#FFD4C8] shadow-sm space-y-3 mt-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="p-2 rounded-xl bg-[#FF5B35] text-white shadow-sm">
                          <Bot className="w-5 h-5" />
                        </div>
                        <div>
                          <h4 className="text-sm font-extrabold text-[#0F172A] flex items-center gap-2">
                            AI Personal Tutor
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse"></span>
                              Active
                            </span>
                          </h4>
                          <p className="text-xs text-[#64748B]">
                            Question {currentQuestion?.number || 1} Discussion & Concept Explanations
                          </p>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => setShowTutorModal(true)}
                        className="px-4 py-2 rounded-xl bg-[#FF5B35] hover:bg-[#E84E29] text-white text-xs font-bold shadow-md shadow-[#FF5B35]/25 hover:scale-105 transition-all flex items-center gap-1.5 cursor-pointer"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                        Ask Tutor
                      </button>
                    </div>

                    <div className="p-3 rounded-xl bg-white/80 border border-[#FFE2D9] text-xs text-[#475569] flex items-center justify-between">
                      <span>💡 Discuss Question {currentQuestion?.number || 1} evaluation and model solutions.</span>
                      <button
                        type="button"
                        onClick={() => {
                          setShowTutorModal(true)
                          handleSendMessage(
                            `Why were marks deducted for Question ${currentQuestion?.number || 1}?`,
                            currentQuestion?.id
                          )
                        }}
                        className="text-[#FF5B35] font-bold hover:underline cursor-pointer"
                      >
                        Ask now →
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Profile Update Modal */}
      {showProfileModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-2xl max-w-md w-full space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <GraduationCap className="w-5 h-5 text-[#FF5B35]" />
                Update Academic Class
              </h3>
              <button
                type="button"
                onClick={() => setShowProfileModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveAcademicProfile} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Semester (Range 1–8)
                </label>
                <select
                  value={profileSemester}
                  onChange={(e) => setProfileSemester(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:outline-none"
                >
                  {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                    <option key={s} value={s}>
                      Semester {s}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Section (1, 2, 3, or 4)
                </label>
                <select
                  value={profileSection}
                  onChange={(e) => setProfileSection(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:outline-none"
                >
                  {[1, 2, 3, 4].map((sec) => (
                    <option key={sec} value={sec}>
                      Section {sec}
                    </option>
                  ))}
                </select>
              </div>

              <div className="pt-2 flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowProfileModal(false)}
                  className="flex-1 py-2.5 rounded-xl bg-slate-100 text-slate-700 text-xs font-bold hover:bg-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={savingProfile}
                  className="flex-1 py-2.5 rounded-xl bg-[#FF5B35] text-white text-xs font-bold shadow-md hover:scale-105 transition-all"
                >
                  {savingProfile ? 'Saving...' : 'Save Class'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Tutor Interactive Chat Modal */}
      {showTutorModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white w-full max-w-2xl h-[650px] rounded-3xl border border-slate-200 shadow-2xl flex flex-col overflow-hidden">
            {/* Modal Header */}
            <div className="p-4 sm:p-5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-orange-50/50 to-white">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-[#FF5B35] text-white flex items-center justify-center shadow-md shadow-[#FF5B35]/20">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-extrabold text-sm sm:text-base text-slate-900 flex items-center gap-2">
                    EduSense AI Personal Tutor
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-orange-100 text-[#FF5B35]">
                      Active
                    </span>
                  </h3>
                  <p className="text-xs text-slate-500">
                    Question {currentQuestion?.number || 1} Context • Grounded in Course Content
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => setShowTutorModal(false)}
                className="p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* In-Modal Question Selector Pills */}
            {questions.length > 1 && (
              <div className="px-4 py-2.5 bg-slate-50 border-b border-slate-100 flex items-center gap-2 overflow-x-auto text-xs">
                <span className="text-[11px] font-bold uppercase text-slate-500 shrink-0">Switch Question:</span>
                {questions.map((q) => {
                  const isCurrent = currentQuestion?.id === q.id
                  return (
                    <button
                      key={q.id}
                      type="button"
                      onClick={() => setSelectedQuestionId(q.id)}
                      className={`px-3 py-1 rounded-xl text-xs font-bold transition-all shrink-0 cursor-pointer ${
                        isCurrent
                          ? 'bg-[#FF5B35] text-white shadow-xs'
                          : 'bg-white hover:bg-slate-200 text-slate-700 border border-slate-200'
                      }`}
                    >
                      Q{q.number}
                    </button>
                  )
                })}
              </div>
            )}

            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-slate-50/50">
              {currentMessages.map((msg) => {
                const isUser = msg.role === 'user'
                return (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} space-y-1`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed shadow-xs ${
                        isUser
                          ? 'bg-[#FF5B35] text-white rounded-br-xs font-medium'
                          : 'bg-white text-slate-800 border border-slate-200/80 rounded-bl-xs'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.content}</p>

                      {/* Citations if returned */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-3 pt-2.5 border-t border-slate-100 space-y-1">
                          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                            Grounded Reference Material:
                          </span>
                          {msg.citations.map((cite, i) => (
                            <div
                              key={i}
                              className="text-[11px] text-[#FF5B35] font-medium flex items-center gap-1"
                            >
                              <ExternalLink className="w-3 h-3" />
                              <span>{cite.source || cite}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400 px-1">
                      {isUser ? 'You' : msg.provider || 'EduSense AI'} • {msg.timestamp || 'Just now'}
                    </span>
                  </div>
                )
              })}

              {isTyping && (
                <div className="flex items-center gap-2 text-xs text-slate-500 bg-white p-3 rounded-2xl border border-slate-200 w-fit">
                  <Loader2 className="w-4 h-4 animate-spin text-[#FF5B35]" />
                  <span>EduSense Tutor is reviewing your response...</span>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Quick Prompt Chips */}
            <div className="px-4 py-2 bg-white border-t border-slate-100 flex items-center gap-2 overflow-x-auto text-xs">
              <span className="text-[10px] font-bold uppercase text-slate-400 shrink-0">Prompts:</span>
              <button
                type="button"
                onClick={() => handleSendMessage(`Why were marks deducted for Question ${currentQuestion?.number || 1}?`, currentQuestion?.id)}
                className="whitespace-nowrap px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs transition-colors cursor-pointer"
              >
                Why did I lose marks?
              </button>
              <button
                type="button"
                onClick={() => handleSendMessage(`Give me a step-by-step model solution for Question ${currentQuestion?.number || 1}.`, currentQuestion?.id)}
                className="whitespace-nowrap px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs transition-colors cursor-pointer"
              >
                Model solution
              </button>
              <button
                type="button"
                onClick={() => handleSendMessage(`How can I master Question ${currentQuestion?.number || 1}'s topic for the next exam?`, currentQuestion?.id)}
                className="whitespace-nowrap px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs transition-colors cursor-pointer"
              >
                Study advice
              </button>
            </div>

            {/* Input Bar */}
            <div className="p-4 bg-white border-t border-slate-100 flex items-center gap-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSendMessage(null, currentQuestion?.id)
                }}
                placeholder={`Ask tutor about Question ${currentQuestion?.number || 1}...`}
                className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-xs sm:text-sm text-slate-900 focus:outline-none focus:border-[#FF5B35]"
              />
              <button
                type="button"
                disabled={!inputMessage.trim() || isTyping}
                onClick={() => handleSendMessage(null, currentQuestion?.id)}
                className="p-3 rounded-xl bg-[#FF5B35] hover:bg-[#E84E29] disabled:opacity-50 text-white font-bold transition-all shadow-md shadow-[#FF5B35]/25 cursor-pointer"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default StudentResultPage
