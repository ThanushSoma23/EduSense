import React, { useState } from 'react'
import { ZoomIn, ZoomOut, RotateCcw, FileText } from 'lucide-react'

export const ScanViewer = ({ imageUrl, studentName = 'Alex Rivera', questionNumber = 1 }) => {
  const [scale, setScale] = useState(1.0)

  const zoomIn = () => setScale((s) => Math.min(s + 0.25, 2.5))
  const zoomOut = () => setScale((s) => Math.max(s - 0.25, 0.75))
  const resetZoom = () => setScale(1.0)

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl overflow-hidden border border-[#E2E8F0] shadow-sm">
      {/* Header bar */}
      <div className="bg-[#FAF8F5] px-4 py-3 border-b border-[#E2E8F0] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-[#FF5B35]" />
          <span className="font-bold text-sm text-[#0F172A]">
            Answer Sheet — Q{questionNumber}
          </span>
          <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-[#FFF0EB] text-[#FF5B35] border border-[#FFD4C8]">
            {studentName}
          </span>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-1.5 bg-white p-1 rounded-lg border border-[#E2E8F0]">
          <button
            onClick={zoomOut}
            className="p-1 rounded hover:bg-slate-100 text-[#64748B] hover:text-[#0F172A] transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <span className="text-xs font-mono px-1 font-bold text-[#FF5B35]">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={zoomIn}
            className="p-1 rounded hover:bg-slate-100 text-[#64748B] hover:text-[#0F172A] transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={resetZoom}
            className="p-1 rounded hover:bg-slate-100 text-[#64748B] hover:text-[#0F172A] transition-colors ml-1"
            title="Reset Zoom"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Cream Paper Frame Container */}
      <div className="flex-1 bg-[#F8FAFC] p-4 overflow-auto flex items-center justify-center min-h-[420px]">
        <div
          className="bg-[#FFFDF9] text-[#0F172A] rounded-xl p-6 shadow-md transition-transform duration-200 border border-[#E2E8F0] max-w-full"
          style={{ transform: `scale(${scale})`, transformOrigin: 'top center' }}
        >
          {/* Paper Header */}
          <div className="border-b border-[#E2E8F0] pb-3 mb-4 flex justify-between items-center text-xs font-serif italic text-[#64748B]">
            <span>CS-301 Answer Script</span>
            <span>Student ID: {studentName}</span>
          </div>

          {/* Sample Handwritten Page Content */}
          <div className="font-serif leading-relaxed text-sm space-y-4 min-h-[300px]">
            <div className="p-3 bg-[#FAF8F5] rounded-lg border border-[#E2E8F0] font-mono text-xs text-[#0F172A]">
              <span className="font-bold text-[#FF5B35]">Q{questionNumber}:</span> (Handwritten student submission crop)
            </div>

            <p className="text-base font-medium tracking-wide text-[#1E293B] leading-relaxed border-l-4 border-[#FF5B35] pl-3 italic">
              "A Binary Search Tree (BST) insertion starts at root node. If value is less than current node, traverse left; if greater, traverse right. Repeat recursively until empty spot (null child) is found, then create new node. Time complexity: average O(log n), worst case O(n) for skewed trees."
            </p>

            <div className="text-xs text-[#64748B] font-mono pt-4 border-t border-[#E2E8F0] flex justify-between">
              <span>High-contrast OCR Scan</span>
              <span className="font-semibold text-emerald-600">Confidence: 96.4%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ScanViewer
