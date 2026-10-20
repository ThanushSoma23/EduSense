import React, { useState, useRef, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Plus, Trash2, Save, FileUp, Sparkles, HelpCircle, Camera, Image, X, RotateCw, AlertCircle, Check, BookOpen, Layers, Edit3 } from 'lucide-react'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

export const ExamSetupPage = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const examId = searchParams.get('exam_id') || searchParams.get('id')

  const [isEditMode, setIsEditMode] = useState(false)
  const [semester, setSemester] = useState('')
  const [section, setSection] = useState(1)
  const [title, setTitle] = useState('')
  const [subject, setSubject] = useState('')
  const [code, setCode] = useState('')

  const [subjectsList, setSubjectsList] = useState([])
  const [loadingSubjects, setLoadingSubjects] = useState(false)
  const [subjectsError, setSubjectsError] = useState(null)

  const [refFile, setRefFile] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // File input refs for desktop and mobile camera
  const fileInputRefs = useRef({})
  const cameraInputRefs = useRef({})

  const [questions, setQuestions] = useState([
    {
      number: 1,
      text: 'Explain Virtual Memory and Paging mechanism.',
      max_marks: 5.0,
      model_answer: 'Virtual memory is a memory management capability of an OS that uses hardware and software to allow a computer to compensate for physical memory shortages. Paging divides virtual memory into page frames.',
      concepts: [
        { id: 'c1', label: 'Virtual Memory compensation' },
        { id: 'c2', label: 'Page frame allocation' }
      ],
      imageFile: null,
      imagePreview: null,
      imageUrl: null,
      ocrLoading: false,
      ocrConfidence: null
    }
  ])

  // Helper to parse rubric into concept badges
  const parseRubricConcepts = (rubricData) => {
    if (!rubricData) return []
    try {
      const parsed = typeof rubricData === 'string' ? JSON.parse(rubricData) : rubricData
      if (Array.isArray(parsed)) {
        return parsed.map((item, idx) => ({
          id: `c-${idx}`,
          label: typeof item === 'string' ? item : item.label || String(item)
        }))
      }
    } catch {
      return [{ id: 'c-0', label: String(rubricData) }]
    }
    return []
  }

  // 1. Load existing exam for edit mode if examId parameter is present
  useEffect(() => {
    if (!examId) return

    const loadExamForEditing = async () => {
      try {
        const res = await api.get(`/exams/${examId}`)
        const ex = res.data
        setIsEditMode(true)
        if (ex.title) setTitle(ex.title)
        if (ex.section) setSection(ex.section)
        if (ex.code) setCode(ex.code)

        if (ex.semester) {
          setSemester(ex.semester)
          // Fetch subjects catalog for the exam's semester
          setLoadingSubjects(true)
          setSubjectsError(null)
          try {
            const sRes = await api.get(`/subjects?semester=${ex.semester}`)
            const list = Array.isArray(sRes.data) ? sRes.data : []
            setSubjectsList(list)
            if (ex.subject) setSubject(ex.subject)
          } catch (sErr) {
            console.warn('Failed to load subjects for exam semester:', sErr)
            setSubjectsError('Failed to load subjects catalog for this semester.')
            if (ex.subject) setSubject(ex.subject)
          } finally {
            setLoadingSubjects(false)
          }
        } else if (ex.subject) {
          setSubject(ex.subject)
        }

        if (Array.isArray(ex.questions) && ex.questions.length > 0) {
          setQuestions(
            ex.questions.map((q, idx) => ({
              number: q.question_number || idx + 1,
              text: q.question_text || '',
              max_marks: q.max_marks || 5.0,
              model_answer: q.model_answer || '',
              concepts: parseRubricConcepts(q.rubric),
              imageFile: null,
              imagePreview: null,
              imageUrl: q.image_url || null,
              ocrLoading: false,
              ocrConfidence: null
            }))
          )
        }
      } catch (err) {
        console.error('Failed to load exam for editing:', err)
        toast.error('Failed to load existing exam details.')
      }
    }

    loadExamForEditing()
  }, [examId])

  // 2. Fetch subjects whenever semester changes (create mode or manual change)
  const fetchSubjectsForSemester = async (semNum) => {
    if (!semNum) {
      setSubjectsList([])
      setLoadingSubjects(false)
      setSubjectsError(null)
      return
    }

    setLoadingSubjects(true)
    setSubjectsError(null)
    try {
      const res = await api.get(`/subjects?semester=${semNum}`)
      const list = Array.isArray(res.data) ? res.data : []
      setSubjectsList(list)
    } catch (err) {
      console.warn('Could not load subjects for semester:', err)
      setSubjectsError(`Unable to load subjects for Semester ${semNum}. Check network or retry.`)
      setSubjectsList([])
    } finally {
      setLoadingSubjects(false)
    }
  }

  // Handle changing semester: automatically clears previously selected subject and code
  const handleSemesterChange = (newSemVal) => {
    const semNum = newSemVal ? Number(newSemVal) : ''
    setSemester(semNum)
    // Clear previously selected subject and course code
    setSubject('')
    setCode('')
    setSubjectsError(null)

    if (semNum) {
      fetchSubjectsForSemester(semNum)
    } else {
      setSubjectsList([])
      setLoadingSubjects(false)
    }
  }

  // Handle selecting a subject from the catalog
  const handleSelectSubject = (val) => {
    setSubject(val)
    const match = subjectsList.find((s) => s.name === val)
    if (match) {
      if (match.code) setCode(match.code)
      if (!title.trim() || title.endsWith(' Midterm') || title.endsWith(' Final Exam')) {
        setTitle(`${match.name} Midterm`)
      }
    }
  }

  const addQuestion = () => {
    setQuestions([
      ...questions,
      {
        number: questions.length + 1,
        text: '',
        max_marks: 5.0,
        model_answer: '',
        concepts: [],
        imageFile: null,
        imagePreview: null,
        imageUrl: null,
        ocrLoading: false,
        ocrConfidence: null
      }
    ])
  }

  const removeQuestion = (index) => {
    if (questions.length === 1) return
    setQuestions(questions.filter((_, i) => i !== index))
  }

  const addConcept = (qIndex, label) => {
    if (!label.trim()) return
    const updated = [...questions]
    updated[qIndex].concepts.push({ id: `c-${Date.now()}`, label: label.trim() })
    setQuestions(updated)
  }

  const removeConcept = (qIndex, cIdx) => {
    const updated = [...questions]
    updated[qIndex].concepts.splice(cIdx, 1)
    setQuestions(updated)
  }

  // Image Upload & Camera Capture Logic
  const handleImageFileChange = (qIndex, file) => {
    if (!file) return

    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']
    if (!allowedTypes.includes(file.type)) {
      toast.error(`Unsupported file type (${file.type || 'unknown'}). Please select a JPEG, PNG, or WebP image.`)
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error(`Image is too large (${(file.size / (1024 * 1024)).toFixed(1)}MB). Maximum allowed size is 5MB.`)
      return
    }

    const previewUrl = URL.createObjectURL(file)
    const updated = [...questions]
    updated[qIndex].imageFile = file
    updated[qIndex].imagePreview = previewUrl
    updated[qIndex].imageUrl = null
    updated[qIndex].ocrConfidence = null
    setQuestions(updated)
    toast.success('Question image attached.')
  }

  const handleRemoveImage = (qIndex) => {
    const updated = [...questions]
    if (updated[qIndex].imagePreview) {
      URL.revokeObjectURL(updated[qIndex].imagePreview)
    }
    updated[qIndex].imageFile = null
    updated[qIndex].imagePreview = null
    updated[qIndex].imageUrl = null
    updated[qIndex].ocrConfidence = null
    setQuestions(updated)
  }

  const handleExtractOcr = async (qIndex) => {
    const q = questions[qIndex]
    if (!q.imageFile) {
      toast.error('No image attached to extract text from.')
      return
    }

    const updated = [...questions]
    updated[qIndex].ocrLoading = true
    setQuestions([...updated])

    try {
      const formData = new FormData()
      formData.append('file', q.imageFile)
      const res = await api.post('/exams/questions/upload-image?run_ocr=true', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      const extracted = res.data.extracted_text || ''
      const confidence = res.data.ocr_confidence || 0.0

      const next = [...questions]
      next[qIndex].ocrLoading = false
      next[qIndex].imageUrl = res.data.image_url
      next[qIndex].ocrConfidence = confidence

      if (extracted) {
        if (next[qIndex].text && next[qIndex].text.trim().length > 0) {
          next[qIndex].text = `${next[qIndex].text}\n${extracted}`
        } else {
          next[qIndex].text = extracted
        }
        toast.success(`Text extracted via OCR (${(confidence * 100).toFixed(0)}% confidence). Please review and edit.`)
      } else {
        toast('Image uploaded, but no text was recognized. You can type the question text below.', { icon: 'ℹ️' })
      }
      setQuestions(next)
    } catch (err) {
      console.error(err)
      const msg = err.response?.data?.detail || 'OCR extraction failed.'
      toast.error(typeof msg === 'string' ? msg : 'OCR extraction failed.')
      const next = [...questions]
      next[qIndex].ocrLoading = false
      setQuestions(next)
    }
  }

  // Submission Handling
  const handleSubmit = async (e) => {
    e.preventDefault()
    if (isSubmitting) return

    // Client-side academic validation
    if (!semester || Number(semester) < 1 || Number(semester) > 8) {
      toast.error('Please select an academic semester first.')
      return
    }
    if (!section || ![1, 2, 3, 4].includes(Number(section))) {
      toast.error('Please select a valid section (1, 2, 3, or 4).')
      return
    }
    if (!subject.trim()) {
      toast.error(`Please select a subject from the Semester ${semester} catalog.`)
      return
    }
    if (!title.trim()) {
      toast.error('Please enter an exam title.')
      return
    }
    if (questions.length === 0) {
      toast.error('Please add at least one question.')
      return
    }

    for (let i = 0; i < questions.length; i++) {
      const q = questions[i]
      if (!q.text.trim() && !q.imageFile) {
        toast.error(`Question ${i + 1} must have either question text or an attached image.`)
        return
      }
      if (!q.model_answer.trim()) {
        toast.error(`Question ${i + 1} requires a model / reference answer for grading.`)
        return
      }
      if (!q.max_marks || q.max_marks <= 0) {
        toast.error(`Question ${i + 1} max marks must be greater than 0.`)
        return
      }
    }

    setIsSubmitting(true)
    try {
      const semInt = parseInt(semester, 10)
      const secInt = parseInt(section, 10)

      if (isEditMode && examId) {
        // Update existing exam class scope & metadata
        await api.put(`/exams/${examId}`, {
          title: title.trim(),
          subject: subject.trim(),
          code: code.trim() || undefined,
          semester: semInt,
          section: secInt
        })
        toast.success('Exam details updated successfully!')
        navigate(`/teacher/upload?exam_id=${examId}`)
        return
      }

      // Create new exam
      const mappedQuestions = questions.map((q, idx) => ({
        question_number: idx + 1,
        number: idx + 1,
        question_text: q.text?.trim() || `[Image Question: ${q.imageFile?.name || 'Attached Diagram'}]`,
        text: q.text?.trim() || `[Image Question: ${q.imageFile?.name || 'Attached Diagram'}]`,
        model_answer: q.model_answer.trim(),
        max_marks: parseFloat(q.max_marks) || 5.0,
        rubric: JSON.stringify(q.concepts.map(c => c.label)),
        concepts: q.concepts,
        image_url: q.imageUrl || null
      }))

      const payload = {
        title: title.trim(),
        subject: subject.trim(),
        code: code.trim() || undefined,
        semester: semInt,
        section: secInt,
        questions: mappedQuestions
      }

      const res = await api.post('/exams', payload)
      const createdExamId = res.data.id || res.data.exam?.id

      toast.success('Exam setup saved successfully!')

      // Upload reference material if attached
      if (refFile && createdExamId) {
        try {
          const formData = new FormData()
          formData.append('file', refFile)
          await api.post(`/exams/${createdExamId}/reference`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          })
          toast.success('Reference material uploaded and indexed.')
        } catch (refErr) {
          console.warn('Reference upload warning:', refErr)
          toast('Exam created. Reference material upload had an issue.', { icon: '⚠️' })
        }
      }

      navigate(`/teacher/upload?exam_id=${createdExamId || 1}`)
    } catch (err) {
      console.error('Exam saving error:', err)
      const detail = err.response?.data?.detail
      let errorMsg = 'Failed to save exam.'
      if (typeof detail === 'string') {
        errorMsg = detail
      } else if (Array.isArray(detail)) {
        errorMsg = detail.map(d => `${d.loc?.slice(-1)[0] || 'field'}: ${d.msg}`).join(', ')
      }
      toast.error(errorMsg)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm border-l-4 border-l-[#FF5B35]">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold font-display text-slate-900">
              {isEditMode ? 'Edit Examination' : 'Create New Exam'}
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Select target academic semester and subject, define questions, model answers, and rubric concepts.
            </p>
          </div>
          {isEditMode && (
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1.5">
              <Edit3 className="w-3.5 h-3.5" />
              Editing Exam #{examId}
            </span>
          )}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Academic Class Structure & Dependent Subject Selection */}
        <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm space-y-6">
          <div>
            <h3 className="text-xl font-bold font-display text-slate-900 flex items-center gap-2">
              <Layers className="w-5 h-5 text-[#FF5B35]" />
              Academic Class & Subject
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Select the semester first. Available subjects will automatically load from the verified curriculum for that semester.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* Step 1: Semester Selector */}
            <div>
              <label htmlFor="exam-semester-select" className="block text-xs font-bold text-slate-700 mb-1.5 flex items-center justify-between">
                <span>1. Academic Semester</span>
                <span className="text-[10px] text-slate-400 font-normal">Sem 1–8</span>
              </label>
              <select
                id="exam-semester-select"
                value={semester}
                onChange={(e) => handleSemesterChange(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-all cursor-pointer"
              >
                <option value="">-- Select Semester --</option>
                {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                  <option key={s} value={s}>
                    Semester {s}
                  </option>
                ))}
              </select>
            </div>

            {/* Step 2: Target Section Selector */}
            <div className="lg:col-span-1">
              <label className="block text-xs font-bold text-slate-700 mb-1.5">
                2. Target Section
              </label>
              <div className="grid grid-cols-4 gap-1.5">
                {[1, 2, 3, 4].map((sec) => {
                  const active = section === sec
                  return (
                    <button
                      key={sec}
                      type="button"
                      onClick={() => setSection(sec)}
                      className={`py-2 text-xs font-extrabold rounded-xl border transition-all cursor-pointer ${
                        active
                          ? 'bg-[#FF5B35] text-white border-[#FF5B35] shadow-sm'
                          : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                      }`}
                    >
                      Sec {sec}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Step 3: Dependent Subject Selector from Backend Catalog */}
            <div className="md:col-span-2">
              <label htmlFor="exam-subject-select" className="block text-xs font-bold text-slate-700 mb-1.5 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-[#FF5B35]" />
                  3. Subject Catalog
                </span>
                <span className="text-[10px] text-slate-400 font-normal">
                  {!semester ? 'Select semester first' : loadingSubjects ? 'Fetching...' : `${subjectsList.length} subjects available`}
                </span>
              </label>
              <select
                id="exam-subject-select"
                disabled={!semester || loadingSubjects}
                value={subject}
                onChange={(e) => handleSelectSubject(e.target.value)}
                className={`w-full border rounded-xl px-3.5 py-2.5 text-sm font-semibold transition-all ${
                  !semester || loadingSubjects
                    ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed'
                    : 'bg-slate-50 text-slate-800 border-slate-200 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none cursor-pointer'
                }`}
              >
                {!semester ? (
                  <option value="">-- Please select a semester first --</option>
                ) : loadingSubjects ? (
                  <option value="">Loading subjects for Semester {semester}...</option>
                ) : subjectsList.length === 0 ? (
                  <option value="">No subjects configured for Semester {semester}</option>
                ) : (
                  <>
                    <option value="">-- Select Subject from Semester {semester} Catalog --</option>
                    {subjectsList.map((s) => (
                      <option key={s.id || s.name} value={s.name}>
                        {s.name} {s.code ? `(${s.code})` : ''}
                      </option>
                    ))}
                  </>
                )}
              </select>

              {/* Subject Loading Indicator */}
              {loadingSubjects && (
                <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1.5 animate-pulse">
                  <RotateCw className="w-3 h-3 animate-spin text-[#FF5B35]" />
                  Fetching subjects for Semester {semester}...
                </p>
              )}

              {/* Recoverable Error State */}
              {subjectsError && (
                <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between text-xs text-red-700">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />
                    <span>{subjectsError}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => fetchSubjectsForSemester(semester)}
                    className="text-xs font-bold text-red-600 hover:text-red-800 underline ml-2 cursor-pointer"
                  >
                    Retry
                  </button>
                </div>
              )}

              {/* Empty Catalog Notice for Semesters 6, 7, 8 */}
              {semester && !loadingSubjects && !subjectsError && subjectsList.length === 0 && (
                <div className="mt-2 p-3 bg-amber-50/80 border border-amber-200 rounded-xl flex items-start gap-2 text-xs text-amber-800">
                  <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">Notice:</span> Subjects have not yet been configured for Semester {semester}.
                    Please choose Semesters 1 through 5, or contact the academic curriculum coordinator.
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Exam Code & Title */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 pt-2">
            <div>
              <label htmlFor="exam-course-code" className="block text-xs font-bold text-slate-700 mb-1">Course Code</label>
              <input
                id="exam-course-code"
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="e.g. CS302"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-colors"
              />
            </div>
            <div className="sm:col-span-2">
              <label htmlFor="exam-title-input" className="block text-xs font-bold text-slate-700 mb-1">Exam Title</label>
              <input
                id="exam-title-input"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                placeholder="e.g. Operating Systems Midterm"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-colors"
              />
            </div>
          </div>

          {/* Scoping Summary Badge */}
          <div className="flex flex-wrap items-center gap-2 pt-2 text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200/80">
            <span className="font-bold text-[#0F172A]">Class Scoping Badge Preview:</span>
            <span className={`px-2.5 py-0.5 rounded-full font-bold border ${
              semester
                ? 'bg-[#FFF0EB] text-[#FF5B35] border-[#FFD4C8]'
                : 'bg-slate-200 text-slate-500 border-slate-300'
            }`}>
              {semester ? `Semester ${semester}` : 'Semester Not Selected'}
            </span>
            <span className="px-2.5 py-0.5 rounded-full font-bold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
              Section {section}
            </span>
            <span className="px-2.5 py-0.5 rounded-full font-bold bg-slate-200 text-slate-800">
              {subject || 'No Subject Selected'} {code ? `(${code})` : ''}
            </span>
          </div>
        </div>

        {/* Reference Material Upload */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm space-y-3">
          <label className="block text-sm font-bold text-slate-800 flex items-center gap-2">
            <FileUp className="w-4 h-4 text-[#FF5B35]" />
            Upload Reference Material (Optional PDF/Textbook Notes for Knowledge Base)
          </label>
          <input
            type="file"
            accept=".pdf,.txt,.docx,.doc"
            onChange={(e) => setRefFile(e.target.files[0])}
            className="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-orange-50 file:text-[#FF5B35] hover:file:bg-orange-100 cursor-pointer"
          />
          {refFile && (
            <p className="text-xs text-emerald-600 font-semibold flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5" /> Selected: {refFile.name} ({(refFile.size / 1024).toFixed(1)} KB)
            </p>
          )}
        </div>

        {/* Questions Builder */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold font-display text-slate-900">Questions & Rubrics</h3>
            <button
              type="button"
              onClick={addQuestion}
              className="px-4 py-2 rounded-xl bg-orange-50 hover:bg-orange-100 text-[#FF5B35] font-bold text-xs flex items-center gap-1.5 transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" /> Add Question
            </button>
          </div>

          {questions.map((q, idx) => (
            <div key={idx} className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <span className="font-extrabold text-sm text-[#FF5B35]">Question {idx + 1}</span>
                {questions.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeQuestion(idx)}
                    className="text-slate-400 hover:text-rose-500 transition-colors cursor-pointer"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Question Image Attachment & Camera Option */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-slate-700">Question Diagram / Photo (Optional)</label>
                <div className="flex flex-wrap items-center gap-3">
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    ref={(el) => (fileInputRefs.current[idx] = el)}
                    onChange={(e) => handleImageFileChange(idx, e.target.files[0])}
                    className="hidden"
                  />
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    capture="environment"
                    ref={(el) => (cameraInputRefs.current[idx] = el)}
                    onChange={(e) => handleImageFileChange(idx, e.target.files[0])}
                    className="hidden"
                  />

                  <button
                    type="button"
                    onClick={() => fileInputRefs.current[idx]?.click()}
                    className="px-3.5 py-2 rounded-xl border border-slate-200 hover:border-[#FF5B35] bg-slate-50 hover:bg-white text-xs font-bold text-slate-700 flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <Image className="w-3.5 h-3.5 text-[#FF5B35]" />
                    Upload Image
                  </button>

                  <button
                    type="button"
                    onClick={() => cameraInputRefs.current[idx]?.click()}
                    className="px-3.5 py-2 rounded-xl border border-slate-200 hover:border-[#FF5B35] bg-slate-50 hover:bg-white text-xs font-bold text-slate-700 flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <Camera className="w-3.5 h-3.5 text-blue-600" />
                    Take Photo
                  </button>

                  {q.imageFile && (
                    <button
                      type="button"
                      disabled={q.ocrLoading}
                      onClick={() => handleExtractOcr(idx)}
                      className="px-3.5 py-2 rounded-xl bg-orange-50 hover:bg-orange-100 text-[#FF5B35] text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      {q.ocrLoading ? 'Extracting via OCR...' : 'Auto-Extract Text (OCR)'}
                    </button>
                  )}
                </div>

                {/* Preview Thumbnail */}
                {q.imagePreview && (
                  <div className="relative inline-block mt-2 border border-slate-200 rounded-xl overflow-hidden shadow-xs">
                    <img src={q.imagePreview} alt="Question preview" className="h-28 object-contain bg-slate-50" />
                    <button
                      type="button"
                      onClick={() => handleRemoveImage(idx)}
                      className="absolute top-1 right-1 p-1 rounded-full bg-slate-900/70 text-white hover:bg-rose-600 transition-colors cursor-pointer"
                      title="Remove image"
                    >
                      <X className="w-3 h-3" />
                    </button>
                    {q.ocrConfidence !== null && (
                      <span className="absolute bottom-1 left-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-black/60 text-white">
                        OCR: {(q.ocrConfidence * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Question Text */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="md:col-span-3">
                  <label className="block text-xs font-bold text-slate-700 mb-1">Question Text</label>
                  <textarea
                    rows={2}
                    value={q.text}
                    onChange={(e) => {
                      const updated = [...questions]
                      updated[idx].text = e.target.value
                      setQuestions(updated)
                    }}
                    placeholder="Enter the question text or problem statement..."
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Max Marks</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    value={q.max_marks}
                    onChange={(e) => {
                      const updated = [...questions]
                      updated[idx].max_marks = parseFloat(e.target.value) || 0
                      setQuestions(updated)
                    }}
                    required
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm font-bold text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-colors"
                  />
                </div>
              </div>

              {/* Reference Answer */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1 flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-emerald-600" />
                  Model / Reference Answer (Ground Truth for AI Grading)
                </label>
                <textarea
                  rows={3}
                  value={q.model_answer}
                  onChange={(e) => {
                    const updated = [...questions]
                    updated[idx].model_answer = e.target.value
                    setQuestions(updated)
                  }}
                  required
                  placeholder="Provide the ideal answer or key points expected from students..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-colors"
                />
              </div>

              {/* Rubric Concepts */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-slate-700">Rubric Concepts (Used by AI Evaluation)</label>
                <div className="flex flex-wrap gap-2">
                  {q.concepts.map((c, cIdx) => (
                    <span key={cIdx} className="px-3 py-1 rounded-full text-xs font-medium bg-orange-50 text-[#FF5B35] border border-orange-200/80 flex items-center gap-1.5">
                      {c.label}
                      <button
                        type="button"
                        onClick={() => removeConcept(idx, cIdx)}
                        className="text-[#FF5B35] hover:text-rose-700 cursor-pointer"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2 pt-1">
                  <input
                    type="text"
                    placeholder="Add concept requirement and press Enter..."
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addConcept(idx, e.target.value)
                        e.target.value = ''
                      }
                    }}
                    className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-xs text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none flex-1 max-w-sm transition-colors"
                  />
                  <span className="text-[11px] text-slate-400 self-center">Press Enter to add concept</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isSubmitting || !semester || !subject.trim()}
          className="w-full py-4 rounded-xl bg-[#FF5B35] hover:bg-[#e04f2d] text-white font-bold text-sm shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <>
              <RotateCw className="w-5 h-5 animate-spin" />
              {isEditMode ? 'Updating Exam Details...' : 'Saving Exam & Questions...'}
            </>
          ) : (
            <>
              <Save className="w-5 h-5" />
              {isEditMode ? 'Update Exam Details' : 'Save Exam & Proceed to Sheet Upload'}
            </>
          )}
        </button>
      </form>
    </div>
  )
}

export default ExamSetupPage
