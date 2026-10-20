import React, { useState, useEffect } from 'react'
import { ShieldCheck, UserX, Clock, CheckCircle2 } from 'lucide-react'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

export const AdminDashboard = () => {
  const [pendingTeachers, setPendingTeachers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchPendingTeachers()
  }, [])

  const fetchPendingTeachers = async () => {
    try {
      const res = await api.get('/admin/pending-teachers')
      setPendingTeachers(res.data.pending_teachers || [])
    } catch (err) {
      console.error(err)
      toast.error('Failed to load pending teacher registrations.')
    } finally {
      setLoading(false)
    }
  }

  const handleApproveOrReject = async (teacherId, action) => {
    try {
      const res = await api.post('/admin/approve-teacher', {
        teacher_id: teacherId,
        action: action
      })
      toast.success(res.data.message)
      fetchPendingTeachers()
    } catch (err) {
      console.error(err)
      toast.error('Action failed.')
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
      <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm border-l-4 border-l-[#FF5B35]">
        <h2 className="text-3xl font-extrabold font-display text-slate-900 flex items-center gap-3">
          Administrator Approvals Portal
        </h2>
        <p className="text-sm text-slate-500 mt-1">
          Review and approve pending institutional teacher registrations.
        </p>
      </div>

      <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm space-y-4">
        <h3 className="text-xl font-bold font-display text-slate-900 flex items-center gap-2">
          <Clock className="w-5 h-5 text-[#FF5B35]" />
          Pending Teacher Registrations ({pendingTeachers.length})
        </h3>

        {pendingTeachers.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm italic border border-dashed border-slate-200 rounded-2xl">
            No pending teacher registration applications found.
          </div>
        ) : (
          <div className="space-y-3">
            {pendingTeachers.map((t) => (
              <div key={t.id} className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-4">
                <div>
                  <h4 className="font-bold text-sm text-slate-900">{t.full_name}</h4>
                  <p className="text-xs text-slate-500">{t.email}</p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleApproveOrReject(t.id, 'approve')}
                    className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 font-bold text-xs text-white shadow-sm hover:scale-105 flex items-center gap-1.5 transition-all"
                  >
                    <ShieldCheck className="w-4 h-4" /> Approve
                  </button>
                  <button
                    onClick={() => handleApproveOrReject(t.id, 'reject')}
                    className="px-4 py-2 rounded-xl bg-rose-50 hover:bg-rose-100 font-bold text-xs text-rose-700 border border-rose-200 flex items-center gap-1.5 transition-all"
                  >
                    <UserX className="w-4 h-4" /> Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
