import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { UploadCloud, File, CheckCircle2, ArrowRight, RefreshCw, AlertTriangle } from 'lucide-react'
import { Stepper } from '../components/Stepper'
import { api } from '../lib/api'
import toast from 'react-hot-toast'

export const UploadCenterPage = () => {
  const navigate = useNavigate()
  const [selectedFiles, setSelectedFiles] = useState([])
  const [activeSheets, setActiveSheets] = useState([])
  const [uploading, setUploading] = useState(false)

  const examId = 'e1111111-1111-1111-1111-111111111111' // Seed Exam ID

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files)
    setSelectedFiles(files)
  }

  const handleUploadSubmit = async (e) => {
    e.preventDefault()
    if (!selectedFiles.length) {
      toast.error('Please select at least one answer sheet image/PDF.')
      return
    }

    setUploading(true)
    try {
      const formData = new FormData()
      selectedFiles.forEach((f) => formData.append('files', f))

      const res = await api.post(`/exams/${examId}/sheets`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      toast.success('Answer sheets uploaded! Processing started.')
      setActiveSheets(res.data.sheets || [])
    } catch (err) {
      console.error(err)
      toast.error('Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  // Poll sheet status every 3 seconds
  useEffect(() => {
    if (!activeSheets.length) return

    const interval = setInterval(async () => {
      const updated = await Promise.all(
        activeSheets.map(async (sheet) => {
          try {
            const res = await api.get(`/sheets/${sheet.id}/status`)
            return { ...sheet, status: res.data.status, error: res.data.error }
          } catch (e) {
            return sheet
          }
        })
      )
      setActiveSheets(updated)
    }, 3000)

    return () => clearInterval(interval)
  }, [activeSheets])

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
      <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm border-l-4 border-l-[#FF5B35]">
        <h2 className="text-3xl font-bold font-display text-slate-900">Answer Sheet Upload Center</h2>
        <p className="text-sm text-slate-500 mt-1">
          Upload scanned student answer sheets for automated preprocessing, OCR, segmentation, and concept coverage.
        </p>
      </div>

      {/* Drag and Drop Upload Area */}
      <div className="bg-white p-8 rounded-3xl border-2 border-dashed border-orange-200 text-center space-y-4 hover:border-[#FF5B35] transition-colors shadow-sm">
        <div className="w-16 h-16 rounded-2xl bg-orange-50 text-[#FF5B35] border border-orange-100 flex items-center justify-center mx-auto shadow-sm">
          <UploadCloud className="w-8 h-8" />
        </div>

        <div>
          <h3 className="text-lg font-bold text-slate-900 font-display">Drag & Drop Answer Sheets Here</h3>
          <p className="text-xs text-slate-500 mt-1">Supports PNG, JPG, JPEG, and multi-page PDF scans</p>
        </div>

        <input
          type="file"
          multiple
          accept="image/*,.pdf"
          onChange={handleFileChange}
          id="file-input"
          className="hidden"
        />

        <div className="pt-2">
          <label
            htmlFor="file-input"
            className="px-6 py-3 rounded-xl bg-orange-50 text-[#FF5B35] border border-orange-200 font-bold text-xs inline-flex items-center gap-2 cursor-pointer hover:bg-orange-100 transition-all shadow-sm"
          >
            Select Files from Computer
          </label>
        </div>

        {selectedFiles.length > 0 && (
          <div className="pt-4 border-t border-slate-200 max-w-md mx-auto space-y-2">
            <span className="text-xs font-bold text-slate-700">{selectedFiles.length} file(s) selected:</span>
            <div className="space-y-1">
              {selectedFiles.map((f, i) => (
                <div key={i} className="text-xs text-slate-600 flex items-center justify-center gap-2">
                  <File className="w-3.5 h-3.5 text-[#FF5B35]" />
                  <span>{f.name}</span>
                </div>
              ))}
            </div>
            <button
              onClick={handleUploadSubmit}
              disabled={uploading}
              className="mt-4 px-8 py-3 rounded-xl bg-[#FF5B35] hover:bg-[#e04f2d] font-bold text-xs text-white shadow-md flex items-center justify-center gap-2 mx-auto transition-all"
            >
              {uploading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Launch Agent Pipeline'}
            </button>
          </div>
        )}
      </div>

      {/* Live Pipeline Stepper Tracker */}
      {activeSheets.length > 0 && (
        <div className="bg-white p-6 rounded-3xl border border-slate-200/80 shadow-sm space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold font-display text-slate-900">Live Processing Status</h3>
            <span className="text-xs text-slate-500 flex items-center gap-1.5">
              <RefreshCw className="w-3.5 h-3.5 text-[#FF5B35] animate-spin" />
              Polling every 3s
            </span>
          </div>

          {activeSheets.map((sheet) => (
            <div key={sheet.id} className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-slate-800 font-bold">Sheet ID: {sheet.id}</span>
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-orange-50 text-[#FF5B35] border border-orange-200">
                  Status: {sheet.status}
                </span>
              </div>

              <Stepper currentStatus={sheet.status} />

              {sheet.status === 'ready' && (
                <div className="flex justify-end pt-2">
                  <button
                    onClick={() => navigate('/teacher/review')}
                    className="px-5 py-2.5 rounded-xl bg-[#FF5B35] hover:bg-[#e04f2d] text-white font-bold text-xs shadow-md flex items-center gap-2 hover:scale-105 transition-all"
                  >
                    Open Review Workspace
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
