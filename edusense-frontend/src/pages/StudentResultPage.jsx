import React from 'react'
import { Award, CheckCircle2, XCircle, Sparkles, BookOpen, BarChart3, Bot } from 'lucide-react'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'
import { ScanViewer } from '../components/ScanViewer'

export const StudentResultPage = () => {
  const chartData = [
    { name: 'Q1 (BST)', Awarded: 4.5, Max: 5.0 },
    { name: 'Q2 (Dijkstra)', Awarded: 3.5, Max: 5.0 },
    { name: 'Q3 (Process)', Awarded: 4.0, Max: 5.0 }
  ]

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      {/* Student Result Header */}
      <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm border-l-4 border-l-[#FF5B35] flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-orange-50 text-[#FF5B35] border border-orange-200">
            CS-301 DSA Final Results
          </span>
          <h2 className="text-3xl font-extrabold font-display text-slate-900 mt-1">
            Student Performance Script
          </h2>
          <p className="text-sm text-slate-500">Student: Alex Rivera (ID: 22222222)</p>
        </div>

        <div className="bg-orange-50/50 p-4 rounded-2xl border border-orange-200/80 text-center">
          <span className="text-xs font-bold text-slate-500 uppercase">Final Total Score</span>
          <div className="text-3xl font-extrabold text-[#FF5B35] font-display">
            12.0 <span className="text-base text-slate-400">/ 15.0</span>
          </div>
          <span className="text-xs text-emerald-700 font-bold">80.0% — Grade A</span>
        </div>
      </div>

      {/* Recharts Score Breakdown Chart */}
      <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm space-y-4">
        <h3 className="text-lg font-bold font-display text-slate-900 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-[#FF5B35]" />
          Per-Question Score Breakdown
        </h3>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 5]} />
              <Tooltip
                contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '12px', color: '#0f172a' }}
              />
              <Bar dataKey="Awarded" fill="#FF5B35" radius={[8, 8, 0, 0]} />
              <Bar dataKey="Max" fill="#e2e8f0" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Scanned Viewer & Concept Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-6 h-[480px]">
          <ScanViewer studentName="Alex Rivera" questionNumber={1} />
        </div>

        <div className="lg:col-span-6 bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm space-y-4">
          <h3 className="text-lg font-bold font-display text-slate-900 flex items-center gap-2">
            <Award className="w-5 h-5 text-[#FF5B35]" />
            Teacher Evaluation & Remarks
          </h3>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex justify-between items-center text-xs font-bold text-slate-800">
              <span>Question 1: BST Insertion</span>
              <span className="text-[#FF5B35]">Awarded: 4.5 / 5.0</span>
            </div>
            <p className="text-xs text-slate-600 italic">
              "Well structured answer with clear complexity analysis by Prof. Sarah Jenkins."
            </p>
          </div>

          <div className="space-y-2 pt-2">
            <h4 className="text-xs font-bold text-slate-700 uppercase">Concept Feedback Summary</h4>
            <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2 font-medium">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              Root comparison & O(log n) time complexity fully demonstrated.
            </div>
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-center gap-2 font-medium">
              <XCircle className="w-4 h-4 text-rose-600 shrink-0" />
              Negative edge weight limitation missed in Q2.
            </div>
          </div>

          {/* AI Tutor Placeholder Card */}
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-center space-y-2 pt-4">
            <div className="inline-flex p-2 rounded-xl bg-orange-50 text-[#FF5B35]">
              <Bot className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-bold text-slate-800">AI Personal Tutor</h4>
            <p className="text-xs text-slate-500">Interactive study explanations coming soon in v2.0.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
