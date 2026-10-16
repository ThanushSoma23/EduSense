import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FileText, FileUp, CheckCircle, Clock, Plus, ArrowRight, Eye, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

export const TeacherDashboard = () => {
  const navigate = useNavigate()
  const [exams, setExams] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchExams()
  }, [])

  const fetchExams = async () => {
    try {
      const res = await api.get('/exams')
      const list = Array.isArray(res.data) ? res.data : (res.data?.exams || [])
      setExams(list)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8 text-left">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-3xl border border-[#E2E8F0] shadow-sm border-l-4 border-l-[#FF5B35]">
        <div>
          <h2 className="text-3xl font-extrabold text-[#0F172A] flex items-center gap-3">
            Teacher Workspace
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
              Prof. Sarah Jenkins
            </span>
          </h2>
          <p className="text-sm text-[#64748B] mt-1">
            Review answer scripts, evaluate semantic evidence, and award final marks.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/teacher/exam/new"
            className="px-5 py-2.5 rounded-xl bg-[#FF5B35] hover:bg-[#E84E29] text-white font-bold text-xs flex items-center gap-2 shadow-md shadow-[#FF5B35]/25 hover:scale-105 transition-all"
          >
            <Plus className="w-4 h-4" />
            Create Exam
          </Link>
          <Link
            to="/teacher/upload"
            className="px-5 py-2.5 rounded-xl bg-white hover:bg-slate-50 text-[#0F172A] font-bold text-xs border border-[#CBD5E1] flex items-center gap-2 transition-all shadow-sm"
          >
            <FileUp className="w-4 h-4 text-[#FF5B35]" />
            Upload Answer Sheets
          </Link>
        </div>
      </div>

      {/* Stats Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-5 rounded-2xl border border-[#E2E8F0] shadow-sm border-l-4 border-l-[#FF5B35]">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold text-[#64748B] uppercase">Total Exams</span>
            <FileText className="w-5 h-5 text-[#FF5B35]" />
          </div>
          <div className="text-3xl font-extrabold text-[#0F172A]">1</div>
          <span className="text-xs text-[#64748B]">CS-301 Data Structures</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-[#E2E8F0] shadow-sm border-l-4 border-l-emerald-500">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold text-[#64748B] uppercase">Sheets Processed</span>
            <Sparkles className="w-5 h-5 text-emerald-500" />
          </div>
          <div className="text-3xl font-extrabold text-[#0F172A]">2</div>
          <span className="text-xs text-emerald-600 font-semibold">100% OCR Segmented</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-[#E2E8F0] shadow-sm border-l-4 border-l-amber-500">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold text-[#64748B] uppercase">Pending Review</span>
            <Clock className="w-5 h-5 text-amber-500" />
          </div>
          <div className="text-3xl font-extrabold text-[#0F172A]">1</div>
          <span className="text-xs text-amber-600 font-semibold">Requires Teacher Decision</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-[#E2E8F0] shadow-sm border-l-4 border-l-indigo-500">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold text-[#64748B] uppercase">Published Results</span>
            <CheckCircle className="w-5 h-5 text-indigo-500" />
          </div>
          <div className="text-3xl font-extrabold text-[#0F172A]">0</div>
          <span className="text-xs text-[#64748B]">Draft Status</span>
        </div>
      </div>

      {/* Active Exams Table */}
      <div className="bg-white rounded-3xl p-6 border border-[#E2E8F0] shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-bold text-[#0F172A]">Active Exams</h3>
          <span className="text-xs text-[#FF5B35] font-bold bg-[#FFF0EB] px-3 py-1 rounded-full border border-[#FFD4C8]">1 Active Course</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#F1F5F9] text-xs text-[#64748B] font-bold uppercase">
                <th className="pb-3 px-4">Code</th>
                <th className="pb-3 px-4">Title</th>
                <th className="pb-3 px-4">Subject</th>
                <th className="pb-3 px-4">Questions</th>
                <th className="pb-3 px-4">Status</th>
                <th className="pb-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F5F9] text-sm">
              <tr className="hover:bg-slate-50/80 transition-colors">
                <td className="py-4 px-4 font-bold text-[#FF5B35]">CS-301</td>
                <td className="py-4 px-4 font-semibold text-[#0F172A]">Data Structures & Algorithms Final</td>
                <td className="py-4 px-4 text-[#475569]">Computer Science</td>
                <td className="py-4 px-4 text-[#475569]">3 Questions</td>
                <td className="py-4 px-4">
                  <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200">
                    Review In Progress
                  </span>
                </td>
                <td className="py-4 px-4 text-right space-x-2">
                  <button
                    onClick={() => navigate('/teacher/review')}
                    className="px-3.5 py-1.5 rounded-lg bg-[#FF5B35] hover:bg-[#E84E29] text-white font-bold text-xs shadow-sm hover:scale-105 transition-all inline-flex items-center gap-1 cursor-pointer"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    Review Workspace
                  </button>
                  <button
                    onClick={() => navigate('/teacher/publish')}
                    className="px-3.5 py-1.5 rounded-lg bg-white hover:bg-slate-50 text-[#0F172A] font-bold text-xs border border-[#CBD5E1] inline-flex items-center gap-1 transition-all cursor-pointer"
                  >
                    Publish Status
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default TeacherDashboard
