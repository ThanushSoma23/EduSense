import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Trash2, Save, FileUp, Sparkles, HelpCircle, Camera, Image, X, RotateCw, AlertCircle, Check, BookOpen, Layers } from 'lucide-react'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

export const ExamSetupPage = () => {
  const navigate = useNavigate()
  const [semester, setSemester] = useState(6)
  const [section, setSection] = useState(1)
  const [title, setTitle] = useState('Operating Systems Midterm')
  const [subject, setSubject] = useState('Operating Systems')
  const [code, setCode] = useState('CS-402')
  const [subjectsList, setSubjectsList] = useState([])
  const [isCustomSubject, setIsCustomSubject] = useState(false)
  const [refFile, setRefFile] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    fetchSubjects()
  }, [])

  const fetchSubjects = async () => {
    try {
      const res = await api.get('/subjects')
      const list = Array.isArray(res.data) ? res.data : []
      setSubjectsList(list)
      if (list.length > 0 && !subject) {
        setSubject(list[0].name)
        if (list[0].code) setCode(list[0].code)
        if (list[0].default_semester) setSemester(list[0].default_semester)
      }
    } catch (err) {
      console.warn('Could not load subjects catalog:', err)
      // Fallback defaults
      setSubjectsList([
        { id: '1', name: 'Operating Systems', code: 'CS-402', default_semester: 6 },
        { id: '2', name: 'Data Structures and Algorithms', code: 'CS-301', default_semester: 3 },
        { id: '3', name: 'Artificial Intelligence', code: 'CS-601', default_semester: 6 },
        { id: '4', name: 'Database Management Systems', code: 'CS-401', default_semester: 4 },
        { id: '5', name: 'Computer Networks', code: 'CS-501', default_semester: 5 }
      ])
    }
  }

  const handleSelectSubject = (val) => {
    if (val === '__custom__') {
      setIsCustomSubject(true)
      setSubject('')
      return
    }
    setIsCustomSubject(false)
    setSubject(val)
    const match = subjectsList.find((s) => s.name === val)
    if (match) {
      if (match.code) setCode(match.code)
      if (match.default_semester) setSemester(match.default_semester)
    }
  }

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

  // --- Issue 3: Image Upload & Camera Capture Logic ---
  const handleImageFileChange = (qIndex, file) => {
    if (!file) return

    // Allowed types: JPEG, PNG, WebP
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']
    if (!allowedTypes.includes(file.type)) {
      toast.error(`Unsupported file type (${file.type || 'unknown'}). Please select a JPEG, PNG, or WebP image.`)
      return
    }

    // Size limit: 5MB
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

  // --- Issue 1: Robust Submission Handling ---
  const handleSubmit = async (e) => {
    e.preventDefault()
    if (isSubmitting) return

    // Client-side validation
    if (!title.trim()) {
      toast.error('Please enter an exam title.')
      return
    }
    if (!subject.trim()) {
      toast.error('Please enter a subject.')
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

    if (!semester || semester < 1 || semester > 8) {
      toast.error('Please select a valid Semester between 1 and 8.')
      return
    }
    if (!section || ![1, 2, 3, 4].includes(Number(section))) {
      toast.error('Please select a valid Section (1, 2, 3, or 4).')
      return
    }
    if (!subject.trim()) {
      toast.error('Please specify a Subject for this exam.')
      return
    }

    setIsSubmitting(true)
    try {
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
        code: code.trim(),
        semester: parseInt(semester, 10),
        section: parseInt(section, 10),
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

      // Navigate to upload center tied to this newly created exam ID
      navigate(`/teacher/upload?exam_id=${createdExamId || 1}`)
    } catch (err) {
      console.error('Exam creation error:', err)
      const detail = err.response?.data?.detail
      let errorMsg = 'Failed to create exam.'
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
      <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm border-l-4 border-l-[#FF5B35]">
        <h2 className="text-3xl font-bold font-display text-slate-900">Create New Exam</h2>
        <p className="text-sm text-slate-500 mt-1">
          Define questions, reference answers, and rubric concepts. You can type text or attach question images/photos.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Step 1: Academic Class & Course Scoping */}
        <div className="bg-white p-6 md:p-8 rounded-3xl border border-slate-200/80 shadow-sm space-y-6">
          <div className="border-b border-slate-100 pb-4">
            <div className="flex items-center gap-2 text-xs font-bold text-[#FF5B35] uppercase tracking-wider mb-1">
              <Layers className="w-4 h-4" />
              <span>Step 1: Academic Scoping</span>
            </div>
            <h3 className="text-xl font-bold font-display text-slate-900">
              Class Structure & Subject Catalog
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Every exam must be scoped to an academic semester and section. Once student submissions exist, this class association is locked.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* Semester Selector */}
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1.5 flex items-center justify-between">
                <span>Semester</span>
                <span className="text-[10px] text-slate-400 font-normal">Range: 1–8</span>
              </label>
              <select
                value={semester}
                onChange={(e) => setSemester(Number(e.target.value))}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-all cursor-pointer"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8].map((s) => (
                  <option key={s} value={s}>
                    Semester {s}
                  </option>
                ))}
              </select>
            </div>

            {/* Section Selector (Buttons) */}
            <div className="lg:col-span-1">
              <label className="block text-xs font-bold text-slate-700 mb-1.5">
                Target Section
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

            {/* Subject Selector from Catalog */}
            <div className="md:col-span-2">
              <label className="block text-xs font-bold text-slate-700 mb-1.5 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-[#FF5B35]" />
                  Subject Catalog
                </span>
                <span className="text-[10px] text-slate-400 font-normal">Standardized Curriculum</span>
              </label>
              <select
                value={isCustomSubject ? '__custom__' : subject}
                onChange={(e) => handleSelectSubject(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm font-semibold text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-all cursor-pointer"
              >
                {subjectsList.map((s) => (
                  <option key={s.id || s.name} value={s.name}>
                    {s.name} {s.code ? `(${s.code})` : ''} {s.default_semester ? `• Sem ${s.default_semester}` : ''}
                  </option>
                ))}
                <option value="__custom__">+ Other / Custom Subject...</option>
              </select>
            </div>
          </div>

          {/* Custom Subject Name Input if selected */}
          {isCustomSubject && (
            <div className="p-4 rounded-2xl bg-orange-50/60 border border-orange-200">
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Custom Subject / Course Name
              </label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Enter subject name (e.g. Distributed Computing)"
                required
                className="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none"
              />
            </div>
          )}

          {/* Exam Code & Title */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 pt-2">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Course Code</label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                placeholder="e.g. CS-402"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-colors"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs font-bold text-slate-700 mb-1">Exam Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                placeholder="e.g. Operating Systems Midterm"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-colors"
              />
            </div>
          </div>

          {/* Summary Pill */}
          <div className="flex flex-wrap items-center gap-2 pt-2 text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200/80">
            <span className="font-bold text-[#0F172A]">Class Scoping Badge Preview:</span>
            <span className="px-2.5 py-0.5 rounded-full font-bold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
              Semester {semester}
            </span>
            <span className="px-2.5 py-0.5 rounded-full font-bold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
              Section {section}
            </span>
            <span className="px-2.5 py-0.5 rounded-full font-bold bg-slate-200 text-slate-800">
              {subject || 'No Subject Selected'} ({code || 'No Code'})
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
              className="px-4 py-2 rounded-xl bg-orange-50 text-[#FF5B35] border border-orange-200/80 font-bold text-xs flex items-center gap-2 hover:bg-orange-100 transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              Add Question
            </button>
          </div>

          {questions.map((q, idx) => (
            <div key={idx} className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm space-y-5 relative">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 rounded-full text-xs font-bold bg-orange-50 text-[#FF5B35] border border-orange-200/80">
                    Question {idx + 1}
                  </span>
                  {q.imageFile && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-600 border border-blue-200">
                      Image Attached
                    </span>
                  )}
                  {q.ocrConfidence !== null && (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      OCR: {(q.ocrConfidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                {questions.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeQuestion(idx)}
                    className="text-slate-400 hover:text-rose-600 transition-colors cursor-pointer p-1"
                    title="Remove question"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Question Text & Max Marks */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="md:col-span-3">
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-xs font-bold text-slate-700">Question Content</label>
                    <span className="text-[11px] text-slate-400">Type text or use image options below</span>
                  </div>
                  <textarea
                    rows={3}
                    value={q.text}
                    onChange={(e) => {
                      const updated = [...questions]
                      updated[idx].text = e.target.value
                      setQuestions(updated)
                    }}
                    placeholder="Enter question text or statement..."
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
                      updated[idx].max_marks = parseFloat(e.target.value) || 5.0
                      setQuestions(updated)
                    }}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-colors"
                  />
                </div>
              </div>

              {/* Issue 3: Image Upload & Mobile Camera Capture Controls */}
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    <Image className="w-3.5 h-3.5 text-[#FF5B35]" />
                    Question Image / Diagram / Camera Capture
                  </span>

                  {/* Hidden file inputs */}
                  <input
                    type="file"
                    ref={(el) => (fileInputRefs.current[idx] = el)}
                    accept="image/jpeg,image/png,image/webp"
                    className="hidden"
                    onChange={(e) => handleImageFileChange(idx, e.target.files[0])}
                  />
                  <input
                    type="file"
                    ref={(el) => (cameraInputRefs.current[idx] = el)}
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={(e) => handleImageFileChange(idx, e.target.files[0])}
                  />

                  {/* Action Buttons */}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => fileInputRefs.current[idx]?.click()}
                      className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:text-[#FF5B35] hover:border-[#FF5B35] text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer"
                    >
                      <Image className="w-3.5 h-3.5" />
                      Upload Image
                    </button>
                    <button
                      type="button"
                      onClick={() => cameraInputRefs.current[idx]?.click()}
                      className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 hover:text-[#FF5B35] hover:border-[#FF5B35] text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer"
                    >
                      <Camera className="w-3.5 h-3.5" />
                      Take Photo
                    </button>
                  </div>
                </div>

                {/* Image Preview & OCR Extract Action */}
                {q.imagePreview && (
                  <div className="p-3 bg-white rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <img
                        src={q.imagePreview}
                        alt={`Question ${idx + 1}`}
                        className="w-16 h-16 object-cover rounded-lg border border-slate-200 shadow-xs"
                      />
                      <div>
                        <p className="text-xs font-bold text-slate-800 truncate max-w-xs">{q.imageFile?.name}</p>
                        <p className="text-[11px] text-slate-500">{(q.imageFile?.size / 1024).toFixed(1)} KB • {q.imageFile?.type}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleExtractOcr(idx)}
                        disabled={q.ocrLoading}
                        className="px-3 py-1.5 rounded-lg bg-orange-50 hover:bg-orange-100 text-[#FF5B35] border border-orange-200 font-bold text-xs flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-50"
                      >
                        {q.ocrLoading ? (
                          <>
                            <RotateCw className="w-3.5 h-3.5 animate-spin" />
                            Extracting...
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-3.5 h-3.5" />
                            Extract Text with OCR
                          </>
                        )}
                      </button>

                      <button
                        type="button"
                        onClick={() => handleRemoveImage(idx)}
                        className="p-1.5 rounded-lg bg-slate-100 hover:bg-rose-50 text-slate-500 hover:text-rose-600 transition-colors cursor-pointer"
                        title="Remove image"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Model / Reference Answer */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Model / Reference Answer</label>
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

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-4 rounded-xl bg-[#FF5B35] hover:bg-[#e04f2d] text-white font-bold text-sm shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
        >
          {isSubmitting ? (
            <>
              <RotateCw className="w-5 h-5 animate-spin" />
              Saving Exam & Questions...
            </>
          ) : (
            <>
              <Save className="w-5 h-5" />
              Save Exam & Proceed to Sheet Upload
            </>
          )}
        </button>
      </form>
    </div>
  )
}

export default ExamSetupPage
