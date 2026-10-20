import React from 'react'
import { Check, Loader2, FileUp, Cpu, Scan, Layers, Sparkles, CheckCircle2 } from 'lucide-react'

export const Stepper = ({ currentStatus = 'uploaded' }) => {
  const steps = [
    { key: 'uploaded', label: 'Uploaded', icon: <FileUp className="w-4 h-4" /> },
    { key: 'preprocessing', label: 'Preprocessing', icon: <Cpu className="w-4 h-4" /> },
    { key: 'ocr', label: 'OCR Extraction', icon: <Scan className="w-4 h-4" /> },
    { key: 'segmenting', label: 'Segmentation', icon: <Layers className="w-4 h-4" /> },
    { key: 'evaluating', label: 'AI Evaluation', icon: <Sparkles className="w-4 h-4" /> },
    { key: 'ready', label: 'Ready for Review', icon: <CheckCircle2 className="w-4 h-4" /> }
  ]

  const statusOrder = ['uploaded', 'preprocessing', 'ocr', 'segmenting', 'evaluating', 'ready']
  const currentIndex = statusOrder.indexOf(currentStatus)

  return (
    <div className="w-full py-4 px-2">
      <div className="flex items-center justify-between relative">
        {/* Connecting Track Line */}
        <div className="absolute top-1/2 left-0 right-0 h-1 bg-slate-200 -translate-y-1/2 z-0 rounded-full" />
        <div
          className="absolute top-1/2 left-0 h-1 bg-[#FF5B35] -translate-y-1/2 z-0 transition-all duration-500 rounded-full"
          style={{ width: `${(Math.max(0, currentIndex) / (steps.length - 1)) * 100}%` }}
        />

        {/* Step Nodes */}
        {steps.map((step, idx) => {
          const isDone = idx < currentIndex || currentStatus === 'ready'
          const isCurrent = idx === currentIndex && currentStatus !== 'ready'

          return (
            <div key={step.key} className="relative z-10 flex flex-col items-center">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-xs transition-all duration-300 ${
                  isDone
                    ? 'bg-emerald-500 text-white shadow-md shadow-emerald-500/20'
                    : isCurrent
                    ? 'bg-[#FF5B35] text-white ring-4 ring-orange-200 shadow-md shadow-[#FF5B35]/25 animate-pulse'
                    : 'bg-slate-100 text-slate-400 border border-slate-200'
                }`}
              >
                {isDone ? <Check className="w-5 h-5 stroke-[3]" /> : isCurrent ? <Loader2 className="w-5 h-5 animate-spin" /> : step.icon}
              </div>
              <span className={`text-[11px] font-bold mt-2 text-center transition-colors ${isCurrent ? 'text-[#FF5B35]' : isDone ? 'text-emerald-700' : 'text-slate-400'}`}>
                {step.label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
