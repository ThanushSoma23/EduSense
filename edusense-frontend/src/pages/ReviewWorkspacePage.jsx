import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  FileText, CheckCircle2, AlertTriangle, Edit3, ChevronLeft, ChevronRight,
  Award, ShieldAlert, Sparkles, RefreshCw, ArrowRight, Save, Check
} from 'lucide-react'
import { ScanViewer } from '../components/ScanViewer'
import { SimilarityRing } from '../components/SimilarityRing'
import { ConceptChip } from '../components/ConceptChip'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

export const ReviewWorkspacePage = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const examId = searchParams.get('exam_id') || ''
  const submissionId = searchParams.get('submission_id') || ''

  // Loading and core state
  const [loading, setLoading] = useState(true)
  const [examInfo, setExamInfo] = useState(null)
  const [studentInfo, setStudentInfo] = useState(null)
  const [submissionInfo, setSubmissionInfo] = useState(null)
  const [questions, setQuestions] = useState([])
  const [currentQIndex, setCurrentQIndex] = useState(0)

  // Question-specific editor state
  const [transcriptText, setTranscriptText] = useState('')
  const [isEditingTranscript, setIsEditingTranscript] = useState(false)
  const [savingTranscript, setSavingTranscript] = useState(false)
  const [finalMarksInput, setFinalMarksInput] = useState('0')
  const [remarksInput, setRemarksInput] = useState('')
  const [submittingMarks, setSubmittingMarks] = useState(false)

  // Fetch live review workspace data
  useEffect(() => {
    const fetchReviewData = async () => {
      setLoading(true)
      try {
        if (submissionId) {
          const res = await api.get(`/submissions/${submissionId}/review`)
          const data = res.data
          setExamInfo(data.exam)
          setStudentInfo(data.student)
          setSubmissionInfo(data.submission)
          setQuestions(data.questions || [])
        } else if (examId) {
          // Fallback if accessed without submission_id
          const examRes = await api.get(`/exams/${examId}`)
          setExamInfo(examRes.data)
          // Look for first submission of this exam
          try {
            const subRes = await api.get(`/submissions?exam_id=${examId}`)
            const subs = subRes.data || []
            if (subs.length > 0) {
              const firstSub = subs[0]
              const fullSubRes = await api.get(`/submissions/${firstSub.id}/review`)
              setStudentInfo(fullSubRes.data.student)
              setSubmissionInfo(fullSubRes.data.submission)
              setQuestions(fullSubRes.data.questions || [])
            }
          } catch (subErr) {
            console.warn('No submission found for exam:', subErr)
          }
        }
      } catch (err) {
        console.error('Failed to load review workspace data:', err)
        toast.error('Failed to load submission review data.')
      } finally {
        setLoading(false)
      }
    }

    fetchReviewData()
  }, [examId, submissionId])

  // Sync state whenever current question index changes
  const currentQ = questions[currentQIndex] || null

  useEffect(() => {
    if (currentQ) {
      const initialText = currentQ.student_answer?.extracted_text || ''
      setTranscriptText(initialText)
      setIsEditingTranscript(false)

      const existingApproved = currentQ.final_mark?.approved_marks
      const suggested = currentQ.evaluation?.suggested_marks
      const defaultMark = existingApproved !== undefined && existingApproved !== null
        ? String(existingApproved)
        : (suggested !== undefined && suggested !== null ? String(suggested) : '0')

      setFinalMarksInput(defaultMark)
      setRemarksInput(currentQ.final_mark?.remarks || '')
    }
  }, [currentQIndex, currentQ])

  // Save teacher-corrected transcript
  const handleSaveTranscript = async () => {
    if (!currentQ || !currentQ.student_answer?.id || !submissionInfo?.id) return

    setSavingTranscript(true)
    try {
      const res = await api.put(
        `/submissions/${submissionInfo.id}/answers/${currentQ.student_answer.id}`,
        { extracted_text: transcriptText }
      )

      toast.success('Transcript updated and AI evaluation re-computed!')
      setIsEditingTranscript(false)

      // Update question in local state
      const updatedQuestions = [...questions]
      updatedQuestions[currentQIndex] = {
        ...currentQ,
        student_answer: {
          ...currentQ.student_answer,
          extracted_text: transcriptText,
          extraction_status: 'CORRECTED',
          needs_review: false
        },
        evaluation: {
          ...currentQ.evaluation,
          similarity_score: res.data.evaluation?.similarity_score,
          concept_coverage: res.data.evaluation?.concept_coverage,
          suggested_marks: res.data.evaluation?.suggested_marks,
          feedback: res.data.evaluation?.feedback,
          evaluation_status: res.data.evaluation?.evaluation_status
        }
      }
      setQuestions(updatedQuestions)

      if (res.data.evaluation?.suggested_marks !== undefined) {
        setFinalMarksInput(String(res.data.evaluation.suggested_marks))
      }
    } catch (err) {
      console.error('Failed to save corrected transcript:', err)
      toast.error('Failed to save transcript corrections.')
    } finally {
      setSavingTranscript(false)
    }
  }

  // Award Final Mark
  const handleAwardMarks = async (marksValue) => {
    if (!currentQ || !currentQ.student_answer?.id) {
      toast.error('No student answer record available to grade.')
      return
    }

    const numericMark = parseFloat(marksValue)
    if (isNaN(numericMark) || numericMark < 0 || numericMark > currentQ.max_marks) {
      toast.error(`Marks must be between 0 and ${currentQ.max_marks}`)
      return
    }

    setSubmittingMarks(true)
    try {
      const payload = {
        final_marks: numericMark,
        award_source: 'teacher_review',
        remarks: remarksInput || 'Approved by teacher'
      }

      const res = await api.post(`/marks/${currentQ.student_answer.id}/award`, payload)

      toast.success(`Successfully awarded ${numericMark} / ${currentQ.max_marks} marks!`)

      // Update local question state
      const updatedQuestions = [...questions]
      updatedQuestions[currentQIndex] = {
        ...currentQ,
        final_mark: {
          id: res.data.mark?.id || 'fm-saved',
          approved_marks: numericMark,
          approval_status: 'APPROVED',
          remarks: remarksInput
        }
      }
      setQuestions(updatedQuestions)
    } catch (err) {
      console.error('Failed to award final mark:', err)
      toast.error(err.response?.data?.detail || 'Failed to award final marks.')
    } finally {
      setSubmittingMarks(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-[500px] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-[#FF5B35] animate-spin" />
          <span className="text-sm font-bold text-slate-600">Loading submission review workspace...</span>
        </div>
      </div>
    )
  }

  if (!currentQ) {
    return (
      <div className="max-w-[800px] mx-auto px-4 py-12 text-center space-y-4">
        <div className="p-8 bg-white rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto" />
          <h2 className="text-lg font-bold text-slate-800">No Reviewable Questions Found</h2>
          <p className="text-sm text-slate-600">
            Could not find questions or submissions for Exam ID {examId} / Submission {submissionId}.
          </p>
          <button
            onClick={() => navigate('/teacher/dashboard')}
            className="px-5 py-2.5 rounded-xl bg-[#FF5B35] text-white font-bold text-xs shadow-md"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  // Token URL for ScanViewer iframe/img
  const token = localStorage.getItem('edusense_token') || localStorage.getItem('token') || ''
  const fileUrlWithAuth = submissionInfo?.file_url
    ? `${api.defaults.baseURL?.replace('/api/v1', '') || ''}${submissionInfo.file_url}?token=${token}`
    : ''

  const similarityScore = currentQ.evaluation?.similarity_score !== null && currentQ.evaluation?.similarity_score !== undefined
    ? Math.round(currentQ.evaluation.similarity_score * 100)
    : 0

  const ocrConfidence = currentQ.student_answer?.ocr_confidence !== undefined && currentQ.student_answer?.ocr_confidence !== null
    ? Math.round(currentQ.student_answer.ocr_confidence * 100)
    : 0

  const extractionStatus = currentQ.student_answer?.extraction_status || 'SUCCESS'
  const isAwarded = Boolean(currentQ.final_mark)

  return (
    <div className="max-w-[1600px] mx-auto px-4 py-6 space-y-4">
      {/* Top Header & Navigation */}
      <div className="bg-white px-6 py-3 rounded-2xl border border-[#E2E8F0] shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 rounded-full text-xs font-extrabold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
            {examInfo?.code || 'EXAM'}
          </span>
          {examInfo?.semester && examInfo?.section && (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-orange-50 text-orange-700 border border-orange-200">
              Sem {examInfo.semester} • Sec {examInfo.section}
            </span>
          )}
          <span className="text-xs font-semibold text-slate-500">
            {examInfo?.subject || 'Exam Evaluation'}
          </span>
          <h2 className="text-base font-bold text-[#0F172A] border-l border-slate-200 pl-3">
            {examInfo?.title || 'Teacher Review Workspace'}
          </h2>
          {studentInfo && (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200">
              Student: {studentInfo.name} ({studentInfo.roll_number || studentInfo.id})
            </span>
          )}
        </div>

        {/* Question Switcher */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentQIndex((i) => Math.max(0, i - 1))}
            disabled={currentQIndex === 0}
            className="p-2 rounded-xl bg-slate-100 border border-[#E2E8F0] text-[#475569] disabled:opacity-30 hover:text-[#0F172A] hover:bg-slate-200 transition-colors cursor-pointer"
            title="Previous Question"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="text-xs font-bold text-[#0F172A] px-2">
            Question {currentQIndex + 1} of {questions.length}
          </span>
          <button
            onClick={() => setCurrentQIndex((i) => Math.min(questions.length - 1, i + 1))}
            disabled={currentQIndex === questions.length - 1}
            className="p-2 rounded-xl bg-slate-100 border border-[#E2E8F0] text-[#475569] disabled:opacity-30 hover:text-[#0F172A] hover:bg-slate-200 transition-colors cursor-pointer"
            title="Next Question"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Main Hero Split Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[640px]">
        {/* Left Column: Scan Viewer (5 cols) */}
        <div className="lg:col-span-5 h-full">
          <ScanViewer
            fileUrl={fileUrlWithAuth}
            fileName={submissionInfo?.file_reference}
            fileType={submissionInfo?.file_reference?.toLowerCase().endsWith('.pdf') ? 'pdf' : 'image'}
            studentName={studentInfo?.name || 'Student'}
            questionNumber={currentQ.number}
          />
        </div>

        {/* Center Column: Transcript & OCR Editor (3 cols) */}
        <div className="lg:col-span-3 bg-white p-5 rounded-2xl border border-[#E2E8F0] shadow-sm flex flex-col space-y-4">
          <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
            <h3 className="font-bold text-sm text-[#0F172A] flex items-center gap-2">
              <FileText className="w-4 h-4 text-[#FF5B35]" />
              OCR Transcript
            </h3>
            <div className="flex items-center gap-2">
              {isEditingTranscript ? (
                <button
                  onClick={handleSaveTranscript}
                  disabled={savingTranscript}
                  className="text-xs font-bold bg-[#FF5B35] text-white px-2.5 py-1 rounded-lg hover:bg-[#E84E29] flex items-center gap-1 cursor-pointer"
                >
                  {savingTranscript ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
                  Save
                </button>
              ) : (
                <button
                  onClick={() => setIsEditingTranscript(true)}
                  className="text-xs font-bold text-[#FF5B35] hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  Edit
                </button>
              )}
            </div>
          </div>

          {/* Status Badge */}
          <div className="flex flex-wrap items-center gap-2">
            {extractionStatus === 'CORRECTED' && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                Teacher Corrected
              </span>
            )}
            {extractionStatus === 'AMBIGUOUS' && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                Ambiguous Question Header
              </span>
            )}
            {extractionStatus === 'UNANSWERED' && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-red-50 text-red-700 border border-red-200">
                Unanswered / Blank
              </span>
            )}
            {extractionStatus === 'SUCCESS' && (
              <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                Clean OCR Extraction
              </span>
            )}
            <span className="px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200">
              Confidence: {ocrConfidence}%
            </span>
          </div>

          {/* Review Warning if needed */}
          {currentQ.student_answer?.needs_review && (
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 flex items-start gap-2 text-xs font-medium">
              <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600 mt-0.5" />
              <span>Please verify this transcript against the scan on the left before awarding marks.</span>
            </div>
          )}

          {/* Question Text Prompt */}
          <div className="p-3 rounded-xl bg-[#FAF8F5] border border-[#E2E8F0] space-y-1">
            <span className="text-[10px] uppercase font-bold text-[#FF5B35]">
              Question {currentQ.number} Prompt ({currentQ.max_marks} marks):
            </span>
            <p className="text-xs text-[#0F172A] font-medium leading-relaxed">{currentQ.text}</p>
          </div>

          {/* Transcript Content / Editable Textarea */}
          <div className="flex-1 space-y-2">
            <label className="block text-[10px] uppercase font-bold text-[#64748B]">
              Student Handwriting Transcript:
            </label>
            {isEditingTranscript ? (
              <textarea
                rows={10}
                value={transcriptText}
                onChange={(e) => setTranscriptText(e.target.value)}
                className="w-full bg-[#FAF8F5] border border-[#FF5B35] rounded-xl p-3 text-xs text-[#0F172A] focus:outline-none leading-relaxed font-mono"
                placeholder="Type or correct student handwriting text..."
              />
            ) : (
              <div className="p-3 rounded-xl bg-[#FAF8F5] border border-[#E2E8F0] text-xs text-[#1E293B] leading-relaxed font-mono whitespace-pre-wrap min-h-[120px]">
                {transcriptText || <span className="text-slate-400 italic">No text extracted for this question.</span>}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Evidence Panel & Teacher Decision Point (4 cols) */}
        <div className="lg:col-span-4 bg-white p-5 rounded-2xl border border-[#E2E8F0] shadow-sm flex flex-col space-y-5">
          <div className="border-b border-[#F1F5F9] pb-3 flex items-center justify-between">
            <h3 className="font-bold text-base text-[#0F172A] flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-[#FF5B35]" />
              AI Evidence & Suggested Range
            </h3>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
              Alignment: {similarityScore}%
            </span>
          </div>

          {/* Similarity Ring & Suggested Marks */}
          <div className="flex items-center justify-around bg-[#FAF8F5] p-4 rounded-2xl border border-[#E2E8F0]">
            <SimilarityRing percentage={similarityScore} size={110} strokeWidth={9} />

            <div className="text-center space-y-1">
              <span className="text-[10px] uppercase font-bold text-[#64748B]">Suggested Mark</span>
              <div className="text-2xl font-extrabold text-[#FF5B35]">
                {currentQ.evaluation?.suggested_marks ?? 0.0}
                <span className="text-sm font-normal text-[#64748B]"> / {currentQ.max_marks}</span>
              </div>
              <span className="text-[10px] text-[#64748B] block max-w-[140px] leading-tight">
                Advisory score from rubric criteria.
              </span>
            </div>
          </div>

          {/* AI Feedback Snippet */}
          {currentQ.evaluation?.feedback && (
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700 leading-relaxed">
              <span className="font-bold block text-slate-900 mb-0.5">Evaluation Feedback:</span>
              {currentQ.evaluation.feedback}
            </div>
          )}

          {/* Concept Chips List */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-[#0F172A] uppercase tracking-wider">
              Rubric Concept Coverage ({currentQ.concepts?.length || 0} Criteria)
            </h4>
            <div className="space-y-2 max-h-[160px] overflow-y-auto pr-1">
              {currentQ.concepts && currentQ.concepts.length > 0 ? (
                currentQ.concepts.map((c, i) => (
                  <ConceptChip
                    key={i}
                    label={c.label}
                    status={c.status}
                    justification={c.justification}
                  />
                ))
              ) : (
                <p className="text-xs text-slate-400 italic">No specific rubric concepts defined for this question.</p>
              )}
            </div>
          </div>

          {/* Human Teacher Decision Point */}
          <div className="pt-4 border-t-2 border-dashed border-[#FFD4C8] space-y-4 bg-[#FFF9F6] p-4 rounded-2xl">
            <div className="flex items-center gap-2 text-xs font-bold text-[#FF5B35]">
              <ShieldAlert className="w-4 h-4 text-[#FF5B35]" />
              <span>Teacher Decision Point (AI suggestions are advisory)</span>
            </div>

            {/* Quick Award Buttons */}
            <div>
              <label className="block text-[11px] font-bold text-[#475569] mb-2">Quick Award Suggestions:</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setFinalMarksInput(String(currentQ.evaluation?.suggested_marks ?? 0))}
                  className="px-3.5 py-1.5 rounded-lg bg-white hover:bg-[#FFF0EB] border border-[#FFD4C8] text-[#FF5B35] text-xs font-bold transition-all shadow-sm cursor-pointer"
                >
                  Give Suggested ({currentQ.evaluation?.suggested_marks ?? 0})
                </button>
                <button
                  type="button"
                  onClick={() => setFinalMarksInput(String(currentQ.max_marks))}
                  className="px-3.5 py-1.5 rounded-lg bg-white hover:bg-[#FFF0EB] border border-[#FFD4C8] text-[#FF5B35] text-xs font-bold transition-all shadow-sm cursor-pointer"
                >
                  Give Max ({currentQ.max_marks})
                </button>
                <button
                  type="button"
                  onClick={() => setFinalMarksInput('0')}
                  className="px-3.5 py-1.5 rounded-lg bg-white hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-bold transition-all shadow-sm cursor-pointer"
                >
                  Give 0
                </button>
              </div>
            </div>

            {/* Final Marks Input & Remarks */}
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-1">
                <label className="block text-[11px] font-bold text-[#0F172A] mb-1">Final Mark</label>
                <input
                  type="number"
                  step="0.5"
                  max={currentQ.max_marks}
                  min={0}
                  value={finalMarksInput}
                  onChange={(e) => setFinalMarksInput(e.target.value)}
                  className="w-full bg-white border-2 border-[#FF5B35] rounded-xl px-3 py-2 text-base font-extrabold text-[#0F172A] focus:outline-none"
                />
              </div>

              <div className="col-span-2">
                <label className="block text-[11px] font-bold text-[#475569] mb-1">Teacher Remarks</label>
                <input
                  type="text"
                  value={remarksInput}
                  onChange={(e) => setRemarksInput(e.target.value)}
                  placeholder="Optional teacher remarks..."
                  className="w-full bg-white border border-[#CBD5E1] rounded-xl px-3 py-2 text-xs text-[#0F172A] focus:border-[#FF5B35] focus:outline-none"
                />
              </div>
            </div>

            {/* Award Button */}
            <button
              type="button"
              onClick={() => handleAwardMarks(finalMarksInput)}
              disabled={submittingMarks}
              className="w-full py-3.5 rounded-xl bg-[#FF5B35] hover:bg-[#E84E29] text-white font-extrabold text-sm shadow-md shadow-[#FF5B35]/30 hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {submittingMarks ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Award className="w-5 h-5" />}
              {isAwarded
                ? `Update Awarded Marks (${finalMarksInput} / ${currentQ.max_marks})`
                : `Award Final Marks (${finalMarksInput} / ${currentQ.max_marks})`}
            </button>

            {isAwarded && (
              <div className="space-y-2">
                <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>
                    Final Mark ({currentQ.final_mark?.approved_marks} / {currentQ.max_marks}) awarded by teacher!
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => navigate(`/teacher/publish?exam_id=${examInfo?.id || examId}`)}
                  className="w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-sm flex items-center justify-center gap-2 transition-all cursor-pointer"
                >
                  Proceed to Publish Results
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ReviewWorkspacePage
