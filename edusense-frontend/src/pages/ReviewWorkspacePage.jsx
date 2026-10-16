import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText, CheckCircle2, AlertTriangle, Edit3, ChevronLeft, ChevronRight,
  Award, ShieldAlert, BookOpen, Sparkles, RefreshCw
} from 'lucide-react'
import { ScanViewer } from '../components/ScanViewer'
import { SimilarityRing } from '../components/SimilarityRing'
import { ConceptChip } from '../components/ConceptChip'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

export const ReviewWorkspacePage = () => {
  const navigate = useNavigate()
  const [currentQIndex, setCurrentQIndex] = useState(0)

  // Demo review state
  const [transcriptText, setTranscriptText] = useState(
    'A Binary Search Tree (BST) insertion starts at root node. If value is less than current node, traverse left; if greater, traverse right. Repeat recursively until empty spot (null child) is found, then create new node. Time complexity: average O(log n), worst case O(n) for skewed trees.'
  )
  const [isEditingTranscript, setIsEditingTranscript] = useState(false)
  const [finalMarksInput, setFinalMarksInput] = useState('4.5')
  const [remarksInput, setRemarksInput] = useState('Well structured answer with clear complexity analysis.')
  const [awardedMark, setAwardedMark] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const sampleQuestions = [
    {
      id: 'a1111111-1111-1111-1111-111111111111',
      number: 1,
      text: 'Explain the concept of Binary Search Tree (BST) insertion and time complexity.',
      max_marks: 5.0,
      model_answer: 'A Binary Search Tree (BST) insertion starts at the root node. If the new value is less than current node, traverse left; if greater, traverse right. Repeat until an empty spot is found, then insert. Average complexity: O(log n), worst case: O(n).',
      similarity: 88.5,
      confidence: 0.96,
      suggested_min: 4.0,
      suggested_max: 4.5,
      concepts: [
        { label: 'Root comparison', status: 'covered', justification: 'Mentions starting insertion at root node.' },
        { label: 'Left/Right traversal condition', status: 'covered', justification: 'States traverse left for smaller, right for greater.' },
        { label: 'O(log n) average time complexity', status: 'covered', justification: 'Correctly cites average O(log n).' },
        { label: 'O(n) worst-case time complexity', status: 'covered', justification: 'Notes O(n) for skewed trees.' }
      ]
    },
    {
      id: 'a2222222-2222-2222-2222-222222222222',
      number: 2,
      text: 'What is Dijkstra\'s Algorithm and what is its primary limitation?',
      max_marks: 5.0,
      model_answer: 'Dijkstra\'s Algorithm is a greedy single-source shortest path algorithm for weighted graphs. It repeatedly selects unvisited node with minimum tentative distance. Limitation: Fails on graphs with negative edge weights.',
      similarity: 62.0,
      confidence: 0.65, // Low confidence flags review
      needs_review: true,
      suggested_min: 3.0,
      suggested_max: 3.5,
      concepts: [
        { label: 'Greedy single-source algorithm', status: 'covered', justification: 'Mentions shortest path greedy selection.' },
        { label: 'Priority queue / Min distance selection', status: 'partial', justification: 'Mentions minimum distance but omits priority queue.' },
        { label: 'Negative edge weights limitation', status: 'missing', justification: 'Negative edge weight limitation is absent.' }
      ]
    }
  ]

  const currentQ = sampleQuestions[currentQIndex]

  const handleAwardMarks = async (marksValue) => {
    setSubmitting(true)
    try {
      const payload = {
        final_marks: parseFloat(marksValue),
        award_source: 'accepted_suggestion',
        remarks: remarksInput
      }
      const res = await api.post(`/marks/${currentQ.id}/award`, payload)
      setAwardedMark(res.data.mark)
      toast.success(`Successfully awarded ${marksValue} / ${currentQ.max_marks} marks!`)
    } catch (err) {
      console.error(err)
      toast.error('Failed to award marks.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-[1600px] mx-auto px-4 py-6 space-y-4">
      {/* Top Header & Navigation */}
      <div className="bg-white px-6 py-3 rounded-2xl border border-[#E2E8F0] shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
            CS-301 DSA Final
          </span>
          <h2 className="text-lg font-bold text-[#0F172A]">
            Teacher Review Workspace
          </h2>
        </div>

        {/* Question Switcher */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentQIndex((i) => Math.max(0, i - 1))}
            disabled={currentQIndex === 0}
            className="p-2 rounded-xl bg-slate-100 border border-[#E2E8F0] text-[#475569] disabled:opacity-30 hover:text-[#0F172A] hover:bg-slate-200 transition-colors cursor-pointer"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="text-xs font-bold text-[#0F172A] px-2">
            Question {currentQIndex + 1} of {sampleQuestions.length}
          </span>
          <button
            onClick={() => setCurrentQIndex((i) => Math.min(sampleQuestions.length - 1, i + 1))}
            disabled={currentQIndex === sampleQuestions.length - 1}
            className="p-2 rounded-xl bg-slate-100 border border-[#E2E8F0] text-[#475569] disabled:opacity-30 hover:text-[#0F172A] hover:bg-slate-200 transition-colors cursor-pointer"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Main Hero Split Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[620px]">
        {/* Left Column: Cream Framed Scan Viewer (5 cols) */}
        <div className="lg:col-span-5 h-full">
          <ScanViewer
            studentName="Alex Rivera"
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
            <button
              onClick={() => setIsEditingTranscript(!isEditingTranscript)}
              className="text-xs font-bold text-[#FF5B35] hover:underline flex items-center gap-1 cursor-pointer"
            >
              <Edit3 className="w-3.5 h-3.5" />
              {isEditingTranscript ? 'Done' : 'Edit'}
            </button>
          </div>

          {/* Low Confidence Review Warning Badge */}
          {currentQ.needs_review && (
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 flex items-center gap-2 text-xs font-bold">
              <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600" />
              <span>Low-confidence OCR scan. Please verify transcript lines.</span>
            </div>
          )}

          {/* Question Text Prompt */}
          <div className="p-3 rounded-xl bg-[#FAF8F5] border border-[#E2E8F0] space-y-1">
            <span className="text-[10px] uppercase font-bold text-[#FF5B35]">Question Prompt:</span>
            <p className="text-xs text-[#0F172A] font-medium leading-relaxed">{currentQ.text}</p>
          </div>

          {/* Transcript Content / Editable Textarea */}
          <div className="flex-1 space-y-2">
            <label className="block text-[10px] uppercase font-bold text-[#64748B]">Student Handwriting Transcript:</label>
            {isEditingTranscript ? (
              <textarea
                rows={10}
                value={transcriptText}
                onChange={(e) => setTranscriptText(e.target.value)}
                className="w-full bg-[#FAF8F5] border border-[#FF5B35] rounded-xl p-3 text-xs text-[#0F172A] focus:outline-none leading-relaxed font-mono"
              />
            ) : (
              <div className="p-3 rounded-xl bg-[#FAF8F5] border border-[#E2E8F0] text-xs text-[#1E293B] leading-relaxed font-mono whitespace-pre-wrap">
                {transcriptText}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: EVIDENCE PANEL & TEACHER DECISION POINT (4 cols) */}
        <div className="lg:col-span-4 bg-white p-5 rounded-2xl border border-[#E2E8F0] shadow-sm flex flex-col space-y-5">
          <div className="border-b border-[#F1F5F9] pb-3 flex items-center justify-between">
            <h3 className="font-bold text-base text-[#0F172A] flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-[#FF5B35]" />
              AI Evidence & Suggested Range
            </h3>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
              Confidence: {Math.round(currentQ.confidence * 100)}%
            </span>
          </div>

          {/* Similarity Ring & Suggested Marks Range */}
          <div className="flex items-center justify-around bg-[#FAF8F5] p-4 rounded-2xl border border-[#E2E8F0]">
            <SimilarityRing percentage={currentQ.similarity} size={110} strokeWidth={9} />

            <div className="text-center space-y-1">
              <span className="text-[10px] uppercase font-bold text-[#64748B]">Suggested Range</span>
              <div className="text-2xl font-extrabold text-[#FF5B35]">
                {currentQ.suggested_min} – {currentQ.suggested_max}
                <span className="text-sm font-normal text-[#64748B]"> / {currentQ.max_marks}</span>
              </div>
              <span className="text-[10px] text-[#64748B] block max-w-[140px] leading-tight">
                Calculated deterministically from rubric coverage.
              </span>
            </div>
          </div>

          {/* Concept Chips List */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-[#0F172A] uppercase tracking-wider">
              Rubric Concept Coverage ({currentQ.concepts.length} Concepts)
            </h4>
            <div className="space-y-2">
              {currentQ.concepts.map((c, i) => (
                <ConceptChip
                  key={i}
                  label={c.label}
                  status={c.status}
                  justification={c.justification}
                />
              ))}
            </div>
          </div>

          {/* HUMAN TEACHER DECISION POINT (THE HERO INVARIANT ACTION) */}
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
                  onClick={() => setFinalMarksInput(currentQ.suggested_max.toString())}
                  className="px-3.5 py-1.5 rounded-lg bg-white hover:bg-[#FFF0EB] border border-[#FFD4C8] text-[#FF5B35] text-xs font-bold transition-all shadow-sm cursor-pointer"
                >
                  Give {currentQ.suggested_max}
                </button>
                <button
                  type="button"
                  onClick={() => setFinalMarksInput(currentQ.suggested_min.toString())}
                  className="px-3.5 py-1.5 rounded-lg bg-white hover:bg-[#FFF0EB] border border-[#FFD4C8] text-[#FF5B35] text-xs font-bold transition-all shadow-sm cursor-pointer"
                >
                  Give {currentQ.suggested_min}
                </button>
                <button
                  type="button"
                  onClick={() => setFinalMarksInput(currentQ.max_marks.toString())}
                  className="px-3.5 py-1.5 rounded-lg bg-white hover:bg-[#FFF0EB] border border-[#FFD4C8] text-[#FF5B35] text-xs font-bold transition-all shadow-sm cursor-pointer"
                >
                  Give Max ({currentQ.max_marks})
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
                  placeholder="Optional feedback..."
                  className="w-full bg-white border border-[#CBD5E1] rounded-xl px-3 py-2 text-xs text-[#0F172A] focus:border-[#FF5B35] focus:outline-none"
                />
              </div>
            </div>

            {/* Distinct Glowing Award Button */}
            <button
              type="button"
              onClick={() => handleAwardMarks(finalMarksInput)}
              disabled={submitting}
              className="w-full py-3.5 rounded-xl bg-[#FF5B35] hover:bg-[#E84E29] text-white font-extrabold text-sm shadow-md shadow-[#FF5B35]/30 hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 cursor-pointer"
            >
              {submitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Award className="w-5 h-5" />}
              Award Final Marks ({finalMarksInput} / {currentQ.max_marks})
            </button>

            {awardedMark && (
              <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-bold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Final Mark awarded by Prof. Sarah Jenkins!</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ReviewWorkspacePage
