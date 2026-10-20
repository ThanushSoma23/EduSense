import React from 'react'
import { CheckCircle2, PieChart, XCircle } from 'lucide-react'

export const ConceptChip = ({ label, status = 'missing', justification }) => {
  const getBadgeStyle = () => {
    switch (status) {
      case 'covered':
        return {
          bg: 'bg-emerald-50/80 border-emerald-200/80',
          badgeClass: 'bg-emerald-100 text-emerald-800 border-emerald-300',
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />,
          symbol: 'Covered'
        }
      case 'partial':
        return {
          bg: 'bg-amber-50/80 border-amber-200/80',
          badgeClass: 'bg-amber-100 text-amber-800 border-amber-300',
          icon: <PieChart className="w-3.5 h-3.5 text-amber-600" />,
          symbol: 'Partial'
        }
      default:
        return {
          bg: 'bg-rose-50/80 border-rose-200/80',
          badgeClass: 'bg-rose-100 text-rose-800 border-rose-300',
          icon: <XCircle className="w-3.5 h-3.5 text-rose-600" />,
          symbol: 'Missing'
        }
    }
  }

  const badge = getBadgeStyle()

  return (
    <div className={`p-3.5 rounded-xl border ${badge.bg} transition-all`}>
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="font-bold text-xs text-[#0F172A]">{label}</span>
        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${badge.badgeClass}`}>
          {badge.icon}
          {badge.symbol}
        </span>
      </div>
      {justification && (
        <p className="text-xs text-[#64748B] italic mt-1 leading-relaxed">
          "{justification}"
        </p>
      )}
    </div>
  )
}

export default ConceptChip
