import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle, AlertTriangle, Send, ShieldCheck } from 'lucide-react'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

export const PublishPage = () => {
  const navigate = useNavigate()
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [publishing, setPublishing] = useState(false)

  const examId = 'e1111111-1111-1111-1111-111111111111'

  useEffect(() => {
    fetchPublishStatus()
  }, [])

  const fetchPublishStatus = async () => {
    try {
      const res = await api.get(`/exams/${examId}/publish-status`)
      setStatus(res.data)
    } catch (err) {
      console.error(err)
      toast.error('Failed to load publish status.')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmPublish = async () => {
    setPublishing(true)
    try {
      await api.post(`/exams/${examId}/publish`)
      toast.success('Exam results published successfully to student view!')
      setShowModal(false)
      fetchPublishStatus()
    } catch (err) {
      console.error(err)
      toast.error('Failed to publish exam.')
    } finally {
      setPublishing(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
      <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm border-l-4 border-l-[#FF5B35]">
        <h2 className="text-3xl font-bold font-display text-slate-900">Publish Exam Results</h2>
        <p className="text-sm text-slate-500 mt-1">
          Results remain completely invisible to students until the teacher explicitly clicks Publish.
        </p>
      </div>

      <div className="bg-white p-8 rounded-3xl border border-slate-200/80 shadow-sm space-y-6">
        <h3 className="text-xl font-bold font-display text-slate-900">Audit Summary</h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-center">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Answer Sheets</span>
            <div className="text-2xl font-extrabold text-slate-900 font-display mt-1">
              {status?.total_sheets || 2}
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-center">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Unawarded Answers</span>
            <div className="text-2xl font-extrabold text-[#FF5B35] font-display mt-1">
              {status?.unawarded_answers || 0}
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-center">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Publication Status</span>
            <div className={`text-lg font-bold mt-2 ${status?.is_published ? 'text-emerald-700' : 'text-amber-600'}`}>
              {status?.is_published ? 'Published' : 'Draft Mode'}
            </div>
          </div>
        </div>

        {status?.is_published ? (
          <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 flex items-center gap-3">
            <CheckCircle className="w-6 h-6 shrink-0 text-emerald-600" />
            <div>
              <h4 className="font-bold text-sm">Exam is Currently Published</h4>
              <p className="text-xs text-emerald-700">Students can now view their evaluated answer scripts and awarded scores.</p>
            </div>
          </div>
        ) : (
          <div className="p-4 rounded-2xl bg-orange-50 border border-orange-200 text-orange-950 flex items-center gap-3">
            <ShieldCheck className="w-6 h-6 shrink-0 text-[#FF5B35]" />
            <div>
              <h4 className="font-bold text-sm text-slate-900">Ready for Official Publication</h4>
              <p className="text-xs text-slate-600">All questions have been reviewed and awarded by Prof. Sarah Jenkins.</p>
            </div>
          </div>
        )}

        <div className="pt-4 flex justify-end">
          <button
            onClick={() => setShowModal(true)}
            disabled={status?.is_published}
            className="px-8 py-3.5 rounded-xl bg-[#FF5B35] hover:bg-[#e04f2d] text-white font-bold text-sm shadow-md hover:shadow-lg disabled:opacity-50 transition-all flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            {status?.is_published ? 'Already Published' : 'Publish Results to Students'}
          </button>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-2xl max-w-md w-full space-y-4">
            <h3 className="text-xl font-bold text-slate-900 font-display flex items-center gap-2">
              <CheckCircle className="w-6 h-6 text-[#FF5B35]" />
              Confirm Publication
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Are you sure you want to publish the final marks for <strong>CS-301 DSA Final</strong>? Students will immediately gain access to their answer sheets, awarded marks, and concept breakdown.
            </p>

            <div className="flex gap-3 pt-2">
              <button
                onClick={() => setShowModal(false)}
                className="flex-1 py-2.5 rounded-xl bg-slate-100 border border-slate-200 text-xs font-bold text-slate-700 hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmPublish}
                disabled={publishing}
                className="flex-1 py-2.5 rounded-xl bg-[#FF5B35] hover:bg-[#e04f2d] text-xs font-bold text-white shadow-md hover:scale-105 transition-all"
              >
                {publishing ? 'Publishing...' : 'Yes, Publish Now'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
