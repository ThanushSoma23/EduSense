import React, { useState, useEffect, useMemo } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import {
  UploadCloud, File, CheckCircle2, ArrowRight, RefreshCw, AlertTriangle,
  Search, User, BookOpen, Check, X, Sparkles, ShieldCheck, ArrowLeft
} from 'lucide-react'
import { Stepper } from '../components/Stepper'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

export const UploadCenterPage = () => {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialExamId = searchParams.get('exam_id') || ''

  // State
  const [exams, setExams] = useState([])
  const [selectedExamId, setSelectedExamId] = useState(initialExamId)
  const [loadingExams, setLoadingExams] = useState(true)

  const [students, setStudents] = useState([])
  const [loadingStudents, setLoadingStudents] = useState(false)
  const [studentSearch, setStudentSearch] = useState('')
  const [selectedStudent, setSelectedStudent] = useState(null)

  const [selectedFile, setSelectedFile] = useState(null)
  const [filePreviewUrl, setFilePreviewUrl] = useState(null)
  const [dragActive, setDragActive] = useState(false)

  const [uploading, setUploading] = useState(false)
  const [submissionResult, setSubmissionResult] = useState(null)
  const [activeSheets, setActiveSheets] = useState([])

  // 1. Fetch Teacher's Exams on mount
  useEffect(() => {
    fetchExams()
  }, [])

  const fetchExams = async () => {
    setLoadingExams(true)
    try {
      const res = await api.get('/exams')
      const list = Array.isArray(res.data) ? res.data : (res.data?.exams || [])
      setExams(list)

      if (list.length > 0) {
        // If query param matched an existing exam, keep it; otherwise default to first exam
        const found = list.find((e) => String(e.id) === String(initialExamId))
        const activeId = found ? String(found.id) : String(list[0].id)
        setSelectedExamId(activeId)
        setSearchParams({ exam_id: activeId })
      }
    } catch (err) {
      console.error('Failed to fetch exams:', err)
      toast.error('Could not load exams.')
    } finally {
      setLoadingExams(false)
    }
  }

  // 2. Fetch Enrolled Students whenever selectedExamId changes
  useEffect(() => {
    if (!selectedExamId) return

    const fetchStudents = async () => {
      setLoadingStudents(true)
      setSelectedStudent(null)
      try {
        const res = await api.get(`/exams/${selectedExamId}/students`)
        const studentList = Array.isArray(res.data) ? res.data : []
        setStudents(studentList)
      } catch (err) {
        console.error('Failed to fetch enrolled students:', err)
        setStudents([])
        toast.error('Failed to load enrolled students for this exam.')
      } finally {
        setLoadingStudents(false)
      }
    }

    fetchStudents()
  }, [selectedExamId])

  const [enrollingSection, setEnrollingSection] = useState(false)

  // Handle Exam Change
  const handleExamChange = (newExamId) => {
    setSelectedExamId(newExamId)
    setSearchParams({ exam_id: newExamId })
    setSelectedStudent(null)
    setStudentSearch('')
    setSubmissionResult(null)
    setActiveSheets([])
  }

  // Batch Enroll Section
  const handleEnrollSection = async () => {
    if (!selectedExamId) return
    const currentEx = exams.find((e) => String(e.id) === String(selectedExamId))
    if (!currentEx || !currentEx.semester || !currentEx.section) {
      toast.error('This exam does not have a semester and section configured.')
      return
    }

    setEnrollingSection(true)
    try {
      const res = await api.post(`/exams/${selectedExamId}/enroll-section`, {
        semester: currentEx.semester,
        section: currentEx.section
      })
      toast.success(res.data.message || `Successfully enrolled section ${currentEx.section}!`)
      // Reload students
      setLoadingStudents(true)
      const sRes = await api.get(`/exams/${selectedExamId}/students`)
      setStudents(Array.isArray(sRes.data) ? sRes.data : [])
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to batch enroll section students.')
    } finally {
      setEnrollingSection(false)
      setLoadingStudents(false)
    }
  }

  // Filter students by search term
  const filteredStudents = useMemo(() => {
    if (!studentSearch.trim()) return students
    const q = studentSearch.toLowerCase()
    return students.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        (s.roll_number && s.roll_number.toLowerCase().includes(q)) ||
        (s.department && s.department.toLowerCase().includes(q))
    )
  }, [students, studentSearch])

  // File Handlers
  const handleFile = (file) => {
    if (!file) return

    const allowed = ['.png', '.jpg', '.jpeg', '.pdf', '.webp']
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (!allowed.includes(ext)) {
      toast.error(`Invalid format ${ext}. Supported: PNG, JPG, JPEG, PDF, WebP`)
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      toast.error('File size exceeds the 10MB limit.')
      return
    }

    setSelectedFile(file)
    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file)
      setFilePreviewUrl(url)
    } else {
      setFilePreviewUrl(null)
    }
  }

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleRemoveFile = () => {
    setSelectedFile(null)
    if (filePreviewUrl) {
      URL.revokeObjectURL(filePreviewUrl)
      setFilePreviewUrl(null)
    }
  }

  // Submit Handler
  const handleUploadSubmit = async (e) => {
    e.preventDefault()
    if (!selectedExamId) {
      toast.error('Please select an exam.')
      return
    }
    if (!selectedStudent) {
      toast.error('Please select an enrolled student.')
      return
    }
    if (!selectedFile) {
      toast.error('Please select or drag an answer sheet file.')
      return
    }

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('student_id', selectedStudent.id)
      formData.append('files', selectedFile)

      const res = await api.post(`/exams/${selectedExamId}/sheets`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      toast.success(res.data.message || 'Answer sheet processed successfully!')
      setSubmissionResult(res.data)
      setActiveSheets(res.data.sheets || [{ id: String(res.data.submission_id), status: 'ready' }])
    } catch (err) {
      console.error('Upload error:', err)
      const detail = err.response?.data?.detail || 'Upload and processing failed.'
      toast.error(detail)
    } finally {
      setUploading(false)
    }
  }

  const handleResetForNext = () => {
    setSelectedStudent(null)
    setSelectedFile(null)
    if (filePreviewUrl) {
      URL.revokeObjectURL(filePreviewUrl)
      setFilePreviewUrl(null)
    }
    setSubmissionResult(null)
    setActiveSheets([])
  }

  const selectedExam = exams.find((e) => String(e.id) === String(selectedExamId))

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-8 text-left">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm border-l-4 border-l-[#FF5B35] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-[#FF5B35] uppercase tracking-wider mb-1">
            <Sparkles className="w-4 h-4" />
            <span>AI-Assisted Evaluation Pipeline</span>
          </div>
          <h2 className="text-3xl font-extrabold font-display text-[#0F172A]">Answer Sheet Upload Center</h2>
          <p className="text-sm text-slate-500 mt-1">
            Assign scanned student sheets to registered course candidates for preprocessing, OCR segmentation, and AI evaluation.
          </p>
        </div>
        <Link
          to="/teacher/dashboard"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors self-start md:self-auto"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Dashboard
        </Link>
      </div>

      {/* Main Submission Form / Results */}
      {!submissionResult ? (
        <form onSubmit={handleUploadSubmit} className="space-y-8">
          {/* STEP 1: SELECT EXAM / COURSE */}
          <div className="bg-white p-6 md:p-8 rounded-3xl border border-slate-200/80 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="w-7 h-7 rounded-full bg-[#FFF0EB] text-[#FF5B35] font-extrabold text-xs flex items-center justify-center border border-[#FFD4C8]">
                  1
                </span>
                <h3 className="text-lg font-bold text-[#0F172A] font-display">Select Exam / Course</h3>
              </div>
              {selectedExam && (
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  {selectedExam.subject || 'Course'} • Total Marks: {selectedExam.total_marks || 50}
                </span>
              )}
            </div>

            {loadingExams ? (
              <div className="py-4 flex items-center gap-2 text-sm text-slate-500">
                <RefreshCw className="w-4 h-4 animate-spin text-[#FF5B35]" />
                Loading exams...
              </div>
            ) : exams.length === 0 ? (
              <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-800 text-sm flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-600" />
                <span>No exams found. Please create an exam first from your teacher dashboard.</span>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                {exams.map((ex) => {
                  const isSelected = String(ex.id) === String(selectedExamId)
                  return (
                    <button
                      key={ex.id}
                      type="button"
                      onClick={() => handleExamChange(String(ex.id))}
                      className={`p-4 rounded-2xl border text-left transition-all ${
                        isSelected
                          ? 'border-[#FF5B35] bg-[#FFF0EB]/40 ring-2 ring-[#FF5B35]/20 shadow-sm'
                          : 'border-slate-200 hover:border-slate-300 bg-white'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-[11px] font-bold text-[#FF5B35] uppercase tracking-wider">
                              {ex.subject || 'CS Course'}
                            </span>
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
                              Sem {ex.semester || '-'} • Sec {ex.section || '-'}
                            </span>
                          </div>
                          <h4 className="text-sm font-bold text-[#0F172A] mt-0.5 line-clamp-1">{ex.title}</h4>
                        </div>
                        {isSelected && (
                          <div className="w-5 h-5 rounded-full bg-[#FF5B35] text-white flex items-center justify-center flex-shrink-0">
                            <Check className="w-3.5 h-3.5 stroke-[3]" />
                          </div>
                        )}
                      </div>
                      <div className="flex items-center gap-3 mt-3 text-xs text-slate-500">
                        <span className="font-mono">Code: {ex.code || `EX-${ex.id}`}</span>
                        <span>•</span>
                        <span>Max: {ex.total_marks || 50} marks</span>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* STEP 2: SELECT REGISTERED STUDENT */}
          <div className="bg-white p-6 md:p-8 rounded-3xl border border-slate-200/80 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="w-7 h-7 rounded-full bg-[#FFF0EB] text-[#FF5B35] font-extrabold text-xs flex items-center justify-center border border-[#FFD4C8]">
                  2
                </span>
                <h3 className="text-lg font-bold text-[#0F172A] font-display">Select Registered Student</h3>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-500">
                  {students.length} student{students.length !== 1 ? 's' : ''} enrolled
                </span>
                {selectedExam?.semester && selectedExam?.section && (
                  <button
                    type="button"
                    onClick={handleEnrollSection}
                    disabled={enrollingSection}
                    className="px-3 py-1.5 rounded-xl bg-orange-50 hover:bg-orange-100 text-[#FF5B35] border border-orange-200 text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    {enrollingSection ? 'Enrolling...' : `Quick Enroll Section ${selectedExam.section}`}
                  </button>
                )}
              </div>
            </div>

            {loadingStudents ? (
              <div className="py-6 flex items-center justify-center gap-2 text-sm text-slate-500">
                <RefreshCw className="w-4 h-4 animate-spin text-[#FF5B35]" />
                Loading enrolled students for this course...
              </div>
            ) : students.length === 0 ? (
              <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-800 text-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="w-5 h-5 flex-shrink-0 text-amber-600" />
                  <div>
                    <p className="font-bold">No students enrolled</p>
                    <p className="text-xs text-amber-700 mt-0.5">
                      There are no registered students enrolled in this exam yet.
                    </p>
                  </div>
                </div>
                {selectedExam?.semester && selectedExam?.section && (
                  <button
                    type="button"
                    onClick={handleEnrollSection}
                    disabled={enrollingSection}
                    className="px-3.5 py-2 rounded-xl bg-[#FF5B35] text-white text-xs font-bold shadow-sm hover:scale-105 transition-all self-start sm:self-auto cursor-pointer disabled:opacity-50"
                  >
                    {enrollingSection ? 'Enrolling...' : `⚡ Enroll All Sem ${selectedExam.semester} Sec ${selectedExam.section} Students`}
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                {/* Search Box */}
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    value={studentSearch}
                    onChange={(e) => setStudentSearch(e.target.value)}
                    placeholder="Search candidate by name, roll number, or department..."
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-[#FF5B35]/20 focus:border-[#FF5B35] text-sm text-slate-800 bg-slate-50/50"
                  />
                  {studentSearch && (
                    <button
                      type="button"
                      onClick={() => setStudentSearch('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {/* Candidate Selection List */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-64 overflow-y-auto p-1">
                  {filteredStudents.length === 0 ? (
                    <div className="col-span-2 py-4 text-center text-xs text-slate-500">
                      No matching students found for "{studentSearch}".
                    </div>
                  ) : (
                    filteredStudents.map((st) => {
                      const isSelected = selectedStudent?.id === st.id
                      return (
                        <div
                          key={st.id}
                          onClick={() => setSelectedStudent(st)}
                          className={`p-3.5 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${
                            isSelected
                              ? 'border-[#FF5B35] bg-[#FFF0EB]/50 ring-2 ring-[#FF5B35]/20 shadow-xs'
                              : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/80 bg-white'
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div
                              className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 ${
                                isSelected ? 'bg-[#FF5B35] text-white' : 'bg-slate-100 text-slate-700'
                              }`}
                            >
                              <User className="w-4 h-4" />
                            </div>
                            <div className="truncate">
                              <div className="text-sm font-bold text-[#0F172A] truncate">{st.name}</div>
                              <div className="text-xs text-slate-500 font-mono flex items-center gap-2 mt-0.5">
                                <span className="text-[#FF5B35] font-semibold">{st.roll_number || `ID: ${st.id}`}</span>
                                <span>•</span>
                                <span className="truncate">{st.department || 'Computer Science'}</span>
                              </div>
                            </div>
                          </div>

                          {isSelected ? (
                            <div className="w-5 h-5 rounded-full bg-[#FF5B35] text-white flex items-center justify-center flex-shrink-0 ml-2">
                              <Check className="w-3.5 h-3.5 stroke-[3]" />
                            </div>
                          ) : (
                            <div className="w-4 h-4 rounded-full border border-slate-300 flex-shrink-0 ml-2" />
                          )}
                        </div>
                      )
                    })
                  )}
                </div>

                {selectedStudent && (
                  <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 flex items-center justify-between text-xs text-emerald-800">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      <span>
                        Selected candidate: <strong>{selectedStudent.name}</strong> ({selectedStudent.roll_number || selectedStudent.id})
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSelectedStudent(null)}
                      className="text-xs text-emerald-700 underline font-semibold hover:text-emerald-900"
                    >
                      Clear
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* STEP 3: UPLOAD ANSWER SHEET */}
          <div className="bg-white p-6 md:p-8 rounded-3xl border border-slate-200/80 shadow-sm space-y-4">
            <div className="flex items-center gap-3">
              <span className="w-7 h-7 rounded-full bg-[#FFF0EB] text-[#FF5B35] font-extrabold text-xs flex items-center justify-center border border-[#FFD4C8]">
                3
              </span>
              <h3 className="text-lg font-bold text-[#0F172A] font-display">Upload Answer Sheet</h3>
            </div>

            {!selectedFile ? (
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={`p-8 rounded-3xl border-2 border-dashed text-center space-y-4 transition-colors ${
                  dragActive
                    ? 'border-[#FF5B35] bg-orange-50/50'
                    : 'border-orange-200 hover:border-[#FF5B35] bg-white'
                }`}
              >
                <div className="w-16 h-16 rounded-2xl bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8] flex items-center justify-center mx-auto shadow-sm">
                  <UploadCloud className="w-8 h-8" />
                </div>

                <div>
                  <h4 className="text-base font-bold text-[#0F172A] font-display">
                    Drag & Drop Answer Sheet Here
                  </h4>
                  <p className="text-xs text-slate-500 mt-1">
                    Supports PNG, JPG, JPEG, WebP, or single/multi-page PDF scans (up to 10MB)
                  </p>
                </div>

                <input
                  type="file"
                  accept=".png,.jpg,.jpeg,.pdf,.webp"
                  onChange={handleFileChange}
                  id="answer-sheet-file"
                  className="hidden"
                />

                <div className="pt-2">
                  <label
                    htmlFor="answer-sheet-file"
                    className="px-6 py-3 rounded-xl bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8] font-bold text-xs inline-flex items-center gap-2 cursor-pointer hover:bg-orange-100 transition-all shadow-sm"
                  >
                    Select File from Computer
                  </label>
                </div>
              </div>
            ) : (
              <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-orange-100 text-[#FF5B35] flex items-center justify-center flex-shrink-0">
                      <File className="w-5 h-5" />
                    </div>
                    <div className="truncate">
                      <p className="text-sm font-bold text-[#0F172A] truncate">{selectedFile.name}</p>
                      <p className="text-xs text-slate-500">
                        {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • {selectedFile.type || 'Document'}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                    title="Remove file"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {filePreviewUrl && (
                  <div className="mt-2 pt-2 border-t border-slate-200">
                    <img
                      src={filePreviewUrl}
                      alt="Answer sheet preview"
                      className="max-h-56 rounded-xl border border-slate-200 object-contain mx-auto bg-white"
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* STEP 4: ASSIGNMENT CONFIRMATION & LAUNCH */}
          <div className="bg-white p-6 md:p-8 rounded-3xl border border-slate-200/80 shadow-sm space-y-5">
            <div className="flex items-center gap-3">
              <span className="w-7 h-7 rounded-full bg-[#FFF0EB] text-[#FF5B35] font-extrabold text-xs flex items-center justify-center border border-[#FFD4C8]">
                4
              </span>
              <h3 className="text-lg font-bold text-[#0F172A] font-display">Assignment Summary & Confirmation</h3>
            </div>

            {/* Summary Details Card */}
            <div className="p-5 rounded-2xl bg-[#FAF8F5] border border-orange-100 space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                <div>
                  <span className="text-slate-400 uppercase font-bold text-[10px] tracking-wider block">Course & Exam</span>
                  <span className="font-bold text-[#0F172A] text-sm mt-0.5 block">
                    {selectedExam ? `${selectedExam.subject || 'CS'} — ${selectedExam.title}` : 'No exam selected'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 uppercase font-bold text-[10px] tracking-wider block">Candidate</span>
                  <span className="font-bold text-[#0F172A] text-sm mt-0.5 block">
                    {selectedStudent ? `${selectedStudent.name} (${selectedStudent.roll_number})` : 'No candidate selected'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 uppercase font-bold text-[10px] tracking-wider block">Attached Sheet</span>
                  <span className="font-bold text-[#0F172A] text-sm mt-0.5 block truncate">
                    {selectedFile ? selectedFile.name : 'No file chosen'}
                  </span>
                </div>
              </div>

              <div className="pt-2 border-t border-orange-200/60 flex items-start gap-2 text-[11px] text-slate-500">
                <ShieldCheck className="w-4 h-4 text-[#FF5B35] flex-shrink-0 mt-0.5" />
                <span>
                  <strong>Strict Governance:</strong> The AI pipeline extracts handwriting and proposes semantic concept coverage scores. Official marks are strictly non-binding and require your manual review and approval.
                </span>
              </div>
            </div>

            {/* Launch Button */}
            <button
              type="submit"
              disabled={uploading || !selectedExamId || !selectedStudent || !selectedFile}
              className={`w-full py-4 rounded-2xl font-bold text-sm shadow-md flex items-center justify-center gap-2 transition-all ${
                uploading || !selectedExamId || !selectedStudent || !selectedFile
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                  : 'bg-[#FF5B35] hover:bg-[#E84E29] text-white hover:scale-[1.01] shadow-[#FF5B35]/25 cursor-pointer'
              }`}
            >
              {uploading ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  <span>Executing Pipeline (Preprocessing, OCR & Semantic Coverage)...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  <span>Confirm Assignment & Process Answer Sheet</span>
                </>
              )}
            </button>
          </div>
        </form>
      ) : (
        /* STEP 5: PIPELINE RESULT & DIRECT REVIEW LINK */
        <div className="bg-white p-6 md:p-8 rounded-3xl border border-slate-200/80 shadow-sm space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center flex-shrink-0">
              <CheckCircle2 className="w-6 h-6 stroke-[2.5]" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-[#0F172A] font-display">
                Answer Sheet Successfully Processed
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                {submissionResult.message || 'Pipeline analysis finished. Suggested concept marks are ready for your review.'}
              </p>
            </div>
          </div>

          {/* Metadata Card */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
            <div>
              <span className="text-slate-400 font-bold uppercase text-[10px] block">Submission ID</span>
              <span className="font-mono font-bold text-[#0F172A] text-sm mt-0.5 block">
                #{submissionResult.submission_id}
              </span>
            </div>
            <div>
              <span className="text-slate-400 font-bold uppercase text-[10px] block">Candidate</span>
              <span className="font-bold text-[#0F172A] text-sm mt-0.5 block">
                {submissionResult.student?.name} ({submissionResult.student?.roll_number})
              </span>
            </div>
            <div>
              <span className="text-slate-400 font-bold uppercase text-[10px] block">Exam</span>
              <span className="font-bold text-[#0F172A] text-sm mt-0.5 block truncate">
                {submissionResult.exam_title || `Exam #${submissionResult.exam_id}`}
              </span>
            </div>
            <div>
              <span className="text-slate-400 font-bold uppercase text-[10px] block">Status</span>
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 mt-0.5">
                Ready for Review
              </span>
            </div>
          </div>

          {/* Stepper Status */}
          <div className="pt-2 pb-2">
            <Stepper currentStatus="ready" />
          </div>

          {/* CTA Actions */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-slate-200">
            <button
              type="button"
              onClick={handleResetForNext}
              className="w-full sm:w-auto px-6 py-3 rounded-xl border border-slate-200 text-slate-700 font-bold text-xs hover:bg-slate-50 transition-colors"
            >
              Upload Another Student's Sheet
            </button>

            <button
              type="button"
              onClick={() =>
                navigate(
                  `/teacher/review?exam_id=${submissionResult.exam_id}&submission_id=${submissionResult.submission_id}`
                )
              }
              className="w-full sm:w-auto px-8 py-3 rounded-xl bg-[#FF5B35] hover:bg-[#E84E29] text-white font-bold text-xs shadow-md shadow-[#FF5B35]/25 flex items-center justify-center gap-2 hover:scale-105 transition-all"
            >
              <span>Proceed to Review Workspace</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
export default UploadCenterPage
