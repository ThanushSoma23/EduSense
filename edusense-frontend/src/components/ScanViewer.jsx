import React, { useState, useMemo, useEffect } from 'react'
import { ZoomIn, ZoomOut, RotateCcw, RotateCw, FileText, ExternalLink, AlertTriangle, RefreshCw, Loader2 } from 'lucide-react'

export const ScanViewer = ({
  fileUrl,
  imageUrl,
  fileName,
  fileType,
  isPdf: isPdfProp,
  studentName = 'Student',
  questionNumber = 1
}) => {
  const [scale, setScale] = useState(1.0)
  const [rotation, setRotation] = useState(0)
  const [loading, setLoading] = useState(true)
  const [hasError, setHasError] = useState(false)
  const [retryKey, setRetryKey] = useState(0)

  const activeUrl = fileUrl || imageUrl

  const token = localStorage.getItem('edusense_token') || localStorage.getItem('token') || ''

  // Attach token query parameter for iframe and direct browser image requests
  const authenticatedUrl = useMemo(() => {
    if (!activeUrl) return ''
    if (activeUrl.startsWith('blob:') || activeUrl.startsWith('data:')) return activeUrl
    if (token && !activeUrl.includes('token=')) {
      const sep = activeUrl.includes('?') ? '&' : '?'
      return `${activeUrl}${sep}token=${encodeURIComponent(token)}`
    }
    return activeUrl
  }, [activeUrl, token, retryKey])

  // Determine whether document is a PDF
  const isPdf = useMemo(() => {
    if (isPdfProp !== undefined) return Boolean(isPdfProp)
    if (fileType === 'pdf' || fileType === 'application/pdf') return true
    if (fileType === 'image' || fileType?.startsWith('image/')) return false
    if (fileName && fileName.toLowerCase().endsWith('.pdf')) return true
    if (activeUrl) {
      const cleanUrl = activeUrl.split('?')[0].toLowerCase()
      if (cleanUrl.endsWith('.pdf') || cleanUrl.includes('.pdf') || cleanUrl.includes('format=pdf')) {
        return true
      }
    }
    return false
  }, [isPdfProp, fileType, fileName, activeUrl])

  useEffect(() => {
    setLoading(Boolean(authenticatedUrl))
    setHasError(false)
  }, [authenticatedUrl])

  const zoomIn = () => setScale((s) => Math.min(s + 0.25, 3.0))
  const zoomOut = () => setScale((s) => Math.max(s - 0.25, 0.5))
  const rotate = () => setRotation((r) => (r + 90) % 360)
  const resetTransform = () => {
    setScale(1.0)
    setRotation(0)
  }

  const handleRetry = () => {
    setHasError(false)
    setLoading(true)
    setRetryKey((k) => k + 1)
  }

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
          {isPdf && (
            <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
              PDF
            </span>
          )}
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {authenticatedUrl && (
            <a
              href={authenticatedUrl}
              target="_blank"
              rel="noreferrer"
              className="p-1.5 rounded-lg bg-white border border-[#E2E8F0] text-[#64748B] hover:text-[#0F172A] hover:bg-slate-50 transition-colors flex items-center gap-1 text-xs font-semibold"
              title="Open Original Document in New Tab"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Open Full</span>
            </a>
          )}

          {!isPdf && authenticatedUrl && (
            <div className="flex items-center gap-1 bg-white p-1 rounded-lg border border-[#E2E8F0]">
              <button
                type="button"
                onClick={zoomOut}
                className="p-1 rounded hover:bg-slate-100 text-[#64748B] hover:text-[#0F172A] transition-colors cursor-pointer"
                title="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              <span className="text-xs font-mono px-1 font-bold text-[#FF5B35]">
                {Math.round(scale * 100)}%
              </span>
              <button
                type="button"
                onClick={zoomIn}
                className="p-1 rounded hover:bg-slate-100 text-[#64748B] hover:text-[#0F172A] transition-colors cursor-pointer"
                title="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={rotate}
                className="p-1 rounded hover:bg-slate-100 text-[#64748B] hover:text-[#0F172A] transition-colors cursor-pointer"
                title="Rotate 90° Clockwise"
              >
                <RotateCw className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={resetTransform}
                className="p-1 rounded hover:bg-slate-100 text-[#64748B] hover:text-[#0F172A] transition-colors cursor-pointer ml-0.5"
                title="Reset View"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Frame Container */}
      <div className="relative flex-1 bg-[#F8FAFC] p-2 overflow-auto flex items-center justify-center min-h-[480px]">
        {authenticatedUrl ? (
          <>
            {loading && (
              <div className="absolute inset-0 bg-slate-50/80 backdrop-blur-xs flex items-center justify-center z-10 gap-2 text-xs font-medium text-slate-500">
                <Loader2 className="w-5 h-5 animate-spin text-[#FF5B35]" />
                <span>Loading original submission...</span>
              </div>
            )}

            {hasError ? (
              <div className="text-center p-8 space-y-3 z-10 max-w-sm">
                <div className="w-12 h-12 rounded-2xl bg-rose-50 border border-rose-200 text-rose-500 flex items-center justify-center mx-auto">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <h4 className="text-sm font-bold text-slate-800">Unable to preview scan</h4>
                  <p className="text-xs text-slate-500">
                    The document could not be rendered inline. You can try opening it directly in a new tab.
                  </p>
                </div>
                <div className="flex items-center justify-center gap-2 pt-1">
                  <button
                    type="button"
                    onClick={handleRetry}
                    className="px-3.5 py-1.5 rounded-xl bg-white border border-slate-200 text-xs font-bold text-slate-700 hover:bg-slate-50 flex items-center gap-1.5 cursor-pointer shadow-xs"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Retry
                  </button>
                  <a
                    href={authenticatedUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="px-3.5 py-1.5 rounded-xl bg-[#FF5B35] text-white text-xs font-bold hover:bg-[#E84E29] flex items-center gap-1.5 cursor-pointer shadow-xs"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Open Full
                  </a>
                </div>
              </div>
            ) : isPdf ? (
              <iframe
                key={`pdf-${retryKey}`}
                src={`${authenticatedUrl}#toolbar=0&navpanes=0`}
                className="w-full h-full min-h-[560px] rounded-xl border border-[#E2E8F0] bg-white shadow-inner"
                title={`Answer Sheet Scan for ${studentName}`}
                onLoad={() => setLoading(false)}
                onError={() => {
                  setLoading(false)
                  setHasError(true)
                }}
              />
            ) : (
              <div
                className="transition-transform duration-200 origin-center flex items-center justify-center w-full h-full"
                style={{
                  transform: `scale(${scale}) rotate(${rotation}deg)`
                }}
              >
                <img
                  key={`img-${retryKey}`}
                  src={authenticatedUrl}
                  alt={`Answer sheet scan for ${studentName}`}
                  className="max-w-full max-h-[580px] rounded-xl shadow-md border border-[#E2E8F0] object-contain bg-white"
                  onLoad={() => setLoading(false)}
                  onError={() => {
                    setLoading(false)
                    setHasError(true)
                  }}
                />
              </div>
            )}
          </>
        ) : (
          <div className="text-center p-8 text-slate-400 space-y-2">
            <FileText className="w-10 h-10 mx-auto text-slate-300" />
            <p className="text-sm font-medium">No answer sheet scan available for preview.</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default ScanViewer
