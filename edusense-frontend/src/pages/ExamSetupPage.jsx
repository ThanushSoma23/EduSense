import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Trash2, Save, FileUp, Sparkles, HelpCircle } from 'lucide-react'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

export const ExamSetupPage = () => {
  const navigate = useNavigate()
  const [title, setTitle] = useState('Operating Systems Midterm')
  const [subject, setSubject] = useState('Computer Science')
  const [code, setCode] = useState('CS-402')
  const [refFile, setRefFile] = useState(null)

  const [questions, setQuestions] = useState([
    {
      number: 1,
      text: 'Explain Virtual Memory and Paging mechanism.',
      max_marks: 5.0,
      model_answer: 'Virtual memory is a memory management capability of an OS that uses hardware and software to allow a computer to compensate for physical memory shortages. Paging divides virtual memory into page frames.',
      concepts: [
        { id: 'c1', label: 'Virtual Memory compensation' },
        { id: 'c2', label: 'Page frame allocation' }
      ]
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
        concepts: []
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

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const payload = { title, subject, code, questions }
      const res = await api.post('/exams', payload)
      toast.success('Exam setup saved successfully!')

      if (refFile && res.data.exam?.id) {
        const formData = new FormData()
        formData.append('file', refFile)
        await api.post(`/exams/${res.data.exam.id}/reference`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        toast.success('Reference material chunked and indexed.')
      }

      navigate('/teacher/upload')
    } catch (err) {
      console.error(err)
      toast.error('Failed to create exam.')
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
      <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm border-l-4 border-l-[#FF5B35]">
        <h2 className="text-3xl font-bold font-display text-slate-900">Create New Exam</h2>
        <p className="text-sm text-slate-500 mt-1">
          Define questions, max marks, model answers, and rubric concepts for automated AI evidence extraction.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Exam Metadata */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Course Code</label>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Subject / Department</label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              required
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Exam Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-colors"
            />
          </div>
        </div>

        {/* Reference Material Upload */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm space-y-3">
          <label className="block text-sm font-bold text-slate-800 flex items-center gap-2">
            <FileUp className="w-4 h-4 text-[#FF5B35]" />
            Upload Reference Material (Optional PDF/Notes for Vector KB)
          </label>
          <input
            type="file"
            onChange={(e) => setRefFile(e.target.files[0])}
            className="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-bold file:bg-orange-50 file:text-[#FF5B35] hover:file:bg-orange-100 cursor-pointer"
          />
        </div>

        {/* Questions Builder */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold font-display text-slate-900">Questions & Rubrics</h3>
            <button
              type="button"
              onClick={addQuestion}
              className="px-4 py-2 rounded-xl bg-orange-50 text-[#FF5B35] border border-orange-200/80 font-bold text-xs flex items-center gap-2 hover:bg-orange-100 transition-all"
            >
              <Plus className="w-4 h-4" />
              Add Question
            </button>
          </div>

          {questions.map((q, idx) => (
            <div key={idx} className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm space-y-4 relative">
              <div className="flex items-center justify-between">
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-orange-50 text-[#FF5B35] border border-orange-200/80">
                  Question {idx + 1}
                </span>
                {questions.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeQuestion(idx)}
                    className="text-slate-400 hover:text-rose-600 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>

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
                    required
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Max Marks</label>
                  <input
                    type="number"
                    step="0.5"
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
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none transition-colors"
                />
              </div>

              {/* Rubric Concepts */}
              <div className="space-y-2">
                <label className="block text-xs font-bold text-slate-700">Rubric Concepts</label>
                <div className="flex flex-wrap gap-2">
                  {q.concepts.map((c, cIdx) => (
                    <span key={cIdx} className="px-3 py-1 rounded-full text-xs font-medium bg-orange-50 text-[#FF5B35] border border-orange-200/80 flex items-center gap-1.5">
                      {c.label}
                    </span>
                  ))}
                </div>
                <div className="flex gap-2 pt-1">
                  <input
                    type="text"
                    placeholder="Add concept requirement..."
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault()
                        addConcept(idx, e.target.value)
                        e.target.value = ''
                      }
                    }}
                    className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-xs text-slate-800 focus:bg-white focus:border-[#FF5B35] focus:ring-1 focus:ring-[#FF5B35] focus:outline-none flex-1 max-w-sm transition-colors"
                  />
                  <span className="text-[11px] text-slate-400 self-center">Press Enter to add chip</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <button
          type="submit"
          className="w-full py-4 rounded-xl bg-[#FF5B35] hover:bg-[#e04f2d] text-white font-bold text-sm shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2"
        >
          <Save className="w-5 h-5" />
          Save Exam & Proceed to Sheet Upload
        </button>
      </form>
    </div>
  )
}
