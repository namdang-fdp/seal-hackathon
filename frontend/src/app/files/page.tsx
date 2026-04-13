'use client'

import { useState, useRef, useCallback } from 'react'
import {
  Upload,
  Image,
  FileText,
  FileSpreadsheet,
  FileType2,
  File,
  Trash2,
  Search,
  HardDrive,
  CheckCircle2,
  Clock,
  Loader2,
  AlertCircle,
  X,
  FolderOpen,
} from 'lucide-react'
import { useDocumentUpload } from '@/hooks/use-document-upload'

/* ── Types ─────────────────────────────────── */

type FileStatus = 'uploading' | 'processing' | 'ready' | 'failed'

interface UploadedFile {
  id: string
  name: string
  type: string
  size: string
  sizeBytes: number
  status: FileStatus
  uploadDate: Date
  progress?: number
  fileKey?: string
  errorMessage?: string
}

/* ── Constants ─────────────────────────────── */

const TOTAL_STORAGE = 100 * 1024 * 1024 // 100 MB

const supportedTypes = [
  { ext: 'PDF', color: 'text-rose-400 bg-rose-500/10 border-rose-500/20' },
  { ext: 'CSV', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' },
  { ext: 'JSON', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
  { ext: 'TXT', color: 'text-sky-400 bg-sky-500/10 border-sky-500/20' },
  { ext: 'MD', color: 'text-purple-400 bg-purple-500/10 border-purple-500/20' },
  { ext: 'XLSX', color: 'text-teal-400 bg-teal-500/10 border-teal-500/20' },
  { ext: 'DOCX', color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
  { ext: 'PNG', color: 'text-pink-400 bg-pink-500/10 border-pink-500/20' },
  { ext: 'JPG', color: 'text-orange-400 bg-orange-500/10 border-orange-500/20' },
  { ext: 'WEBP', color: 'text-lime-400 bg-lime-500/10 border-lime-500/20' },
  { ext: 'SVG', color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20' },
]

/* ── Helpers ────────────────────────────────── */

function getFileIcon(type: string) {
  switch (type) {
    case 'csv':
    case 'xlsx':
      return <FileSpreadsheet className="w-5 h-5" />
    case 'pdf':
      return <FileText className="w-5 h-5" />
    case 'md':
    case 'txt':
      return <FileType2 className="w-5 h-5" />
    case 'png':
    case 'jpg':
    case 'jpeg':
    case 'webp':
    case 'svg':
    case 'gif':
      return <Image className="w-5 h-5" />
    default:
      return <File className="w-5 h-5" />
  }
}

function getFileColor(type: string) {
  switch (type) {
    case 'csv':
    case 'xlsx':
      return 'text-emerald-400 bg-emerald-500/10'
    case 'pdf':
      return 'text-rose-400 bg-rose-500/10'
    case 'json':
      return 'text-amber-400 bg-amber-500/10'
    case 'md':
    case 'txt':
      return 'text-sky-400 bg-sky-500/10'
    case 'docx':
      return 'text-blue-400 bg-blue-500/10'
    case 'png':
      return 'text-pink-400 bg-pink-500/10'
    case 'jpg':
    case 'jpeg':
      return 'text-orange-400 bg-orange-500/10'
    case 'webp':
      return 'text-lime-400 bg-lime-500/10'
    case 'svg':
      return 'text-cyan-400 bg-cyan-500/10'
    case 'gif':
      return 'text-fuchsia-400 bg-fuchsia-500/10'
    default:
      return 'text-zinc-400 bg-zinc-500/10'
  }
}

function getStatusConfig(status: FileStatus) {
  switch (status) {
    case 'uploading':
      return { label: 'Uploading', icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />, color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' }
    case 'processing':
      return { label: 'Processing', icon: <Clock className="w-3.5 h-3.5" />, color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' }
    case 'ready':
      return { label: 'Ready', icon: <CheckCircle2 className="w-3.5 h-3.5" />, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' }
    case 'failed':
      return { label: 'Failed', icon: <AlertCircle className="w-3.5 h-3.5" />, color: 'text-rose-400 bg-rose-500/10 border-rose-500/20' }
  }
}

function formatDate(date: Date) {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (hours < 1) return 'Just now'
  if (hours < 24) return `${hours}h ago`
  if (days < 7) return `${days}d ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

/* ── Page Component ────────────────────────── */

export default function FilesPage() {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [dragActive, setDragActive] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<FileStatus | 'all'>('all')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const usedStorage = files.reduce((sum, f) => sum + f.sizeBytes, 0)
  const storagePercent = (usedStorage / TOTAL_STORAGE) * 100

  const filteredFiles = files.filter(f => {
    const matchesSearch = f.name.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === 'all' || f.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const statusCounts = {
    all: files.length,
    ready: files.filter(f => f.status === 'ready').length,
    processing: files.filter(f => f.status === 'processing').length,
    uploading: files.filter(f => f.status === 'uploading').length,
    failed: files.filter(f => f.status === 'failed').length,
  }

  /* ── Upload hook ──────────────────────────── */

  const { uploadFile } = useDocumentUpload({
    onStatusChange: (fileId, status) => {
      setFiles(prev =>
        prev.map(f => f.id === fileId ? { ...f, status } : f)
      )
    },
    onError: (fileId, error) => {
      setFiles(prev =>
        prev.map(f =>
          f.id === fileId
            ? { ...f, status: 'failed' as FileStatus, errorMessage: error.message }
            : f
        )
      )
    },
  })

  /* ── Event handlers ──────────────────────── */

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const processFiles = useCallback((fileList: FileList) => {
    Array.from(fileList).forEach((file, index) => {
      const ext = file.name.split('.').pop()?.toLowerCase() || ''
      const fileId = `${Date.now()}-${index}`

      const newFile: UploadedFile = {
        id: fileId,
        name: file.name,
        type: ext,
        size: formatBytes(file.size),
        sizeBytes: file.size,
        status: 'uploading',
        uploadDate: new Date(),
      }

      setFiles(prev => [newFile, ...prev])

      // Trigger real upload via the hook
      uploadFile(file, fileId)
    })
  }, [uploadFile])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files?.length) {
      processFiles(e.dataTransfer.files)
    }
  }, [processFiles])

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      processFiles(e.target.files)
    }
  }

  const handleDelete = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id))
    setDeleteConfirm(null)
  }

  return (
    <div className="h-screen overflow-y-auto custom-scrollbar">
      <div className="max-w-6xl mx-auto px-8 py-8 animate-fade-in">
        {/* ── Header ──────────────────────────── */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-zinc-100 mb-2">Files</h1>
          <p className="text-sm text-zinc-500">
            Upload and manage your data files. Once processed, they become available as context in the chat.
          </p>
        </div>

        {/* ── Stats Bar ───────────────────────── */}
        <div className="grid grid-cols-4 gap-4 mb-8 stagger-children">
          <div className="glass rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 rounded-lg bg-violet-500/10 text-violet-400">
                <FolderOpen className="w-5 h-5" />
              </div>
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">Total Files</span>
            </div>
            <p className="text-2xl font-bold text-zinc-100">{files.length}</p>
          </div>

          <div className="glass rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">Ready</span>
            </div>
            <p className="text-2xl font-bold text-zinc-100">{statusCounts.ready}</p>
          </div>

          <div className="glass rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
                <Clock className="w-5 h-5" />
              </div>
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">Processing</span>
            </div>
            <p className="text-2xl font-bold text-zinc-100">{statusCounts.processing + statusCounts.uploading}</p>
          </div>

          <div className="glass rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400">
                <HardDrive className="w-5 h-5" />
              </div>
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">Storage</span>
            </div>
            <p className="text-2xl font-bold text-zinc-100">{formatBytes(usedStorage)}</p>
            <div className="mt-2 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full gradient-violet transition-all duration-500"
                style={{ width: `${Math.min(storagePercent, 100)}%` }}
              />
            </div>
            <p className="text-[11px] text-zinc-600 mt-1">{storagePercent.toFixed(1)}% of {formatBytes(TOTAL_STORAGE)}</p>
          </div>
        </div>

        {/* ── Upload Zone ─────────────────────── */}
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative mb-8 p-10 rounded-2xl border-2 border-dashed cursor-pointer transition-all duration-300 group ${dragActive
              ? 'drop-zone-active'
              : 'border-white/[0.08] bg-white/[0.01] hover:border-violet-500/30 hover:bg-white/[0.02]'
            }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileInput}
            className="hidden"
            accept=".pdf,.csv,.json,.txt,.md,.xlsx,.docx,.png,.jpg,.jpeg,.webp,.svg,.gif"
          />

          <div className="flex flex-col items-center text-center">
            <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 transition-all duration-300 ${dragActive ? 'gradient-violet scale-110' : 'bg-white/[0.04] group-hover:bg-violet-500/10'
              }`}>
              <Upload className={`w-7 h-7 transition-colors duration-300 ${dragActive ? 'text-white' : 'text-zinc-500 group-hover:text-violet-400'
                }`} />
            </div>
            <h3 className="text-base font-semibold text-zinc-200 mb-1">
              {dragActive ? 'Drop files here' : 'Drag & drop files to upload'}
            </h3>
            <p className="text-sm text-zinc-500 mb-4">
              or <span className="text-violet-400 font-medium">browse</span> to select files
            </p>
            <div className="flex flex-wrap justify-center gap-1.5">
              {supportedTypes.map(t => (
                <span
                  key={t.ext}
                  className={`px-2 py-0.5 rounded-md text-[11px] font-semibold border ${t.color}`}
                >
                  {t.ext}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* ── Toolbar ─────────────────────────── */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            {(['all', 'ready', 'processing', 'failed'] as const).map(status => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${statusFilter === status
                    ? 'bg-white/[0.08] text-white'
                    : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04]'
                  }`}
              >
                {status === 'all' ? 'All' : status.charAt(0).toUpperCase() + status.slice(1)}
                <span className="ml-1.5 text-zinc-600">
                  {statusCounts[status]}
                </span>
              </button>
            ))}
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search files..."
              className="pl-9 pr-4 py-2 w-64 rounded-lg bg-white/[0.04] border border-white/[0.06] text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-violet-500/40 transition-all duration-200"
            />
          </div>
        </div>

        {/* ── File List ───────────────────────── */}
        <div className="glass rounded-xl overflow-hidden">
          {/* Table header */}
          <div className="grid grid-cols-[1fr_100px_100px_120px_60px] gap-4 px-5 py-3 border-b border-white/[0.06] bg-white/[0.02]">
            <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">File</span>
            <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Size</span>
            <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Status</span>
            <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Uploaded</span>
            <span />
          </div>

          {filteredFiles.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <FolderOpen className="w-10 h-10 text-zinc-700 mb-3" />
              <p className="text-sm text-zinc-500">No files found</p>
              <p className="text-xs text-zinc-600 mt-1">
                {searchQuery ? 'Try a different search term' : 'Upload your first file to get started'}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-white/[0.03]">
              {filteredFiles.map((file, idx) => {
                const statusConfig = getStatusConfig(file.status)
                return (
                  <div
                    key={file.id}
                    className="grid grid-cols-[1fr_100px_100px_120px_60px] gap-4 px-5 py-3.5 items-center hover:bg-white/[0.02] transition-colors duration-150 group animate-fade-in-up"
                    style={{ animationDelay: `${idx * 40}ms` }}
                  >
                    {/* File name + icon */}
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`p-2 rounded-lg flex-shrink-0 ${getFileColor(file.type)}`}>
                        {getFileIcon(file.type)}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-zinc-200 truncate">{file.name}</p>
                        <p className="text-[11px] text-zinc-600 uppercase">{file.type}</p>
                      </div>
                    </div>

                    {/* Size */}
                    <span className="text-sm text-zinc-400">{file.size}</span>

                    {/* Status badge */}
                    <div>
                      <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-[11px] font-semibold border ${statusConfig.color}`}>
                        {statusConfig.icon}
                        {statusConfig.label}
                      </span>
                    </div>

                    {/* Upload date */}
                    <span className="text-sm text-zinc-500">{formatDate(file.uploadDate)}</span>

                    {/* Actions */}
                    <div className="flex justify-end">
                      {deleteConfirm === file.id ? (
                        <div className="flex items-center gap-1 animate-fade-in">
                          <button
                            onClick={() => handleDelete(file.id)}
                            className="p-1.5 rounded-md bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 transition-colors"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(null)}
                            className="p-1.5 rounded-md bg-white/[0.06] text-zinc-400 hover:bg-white/[0.1] transition-colors"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirm(file.id)}
                          className="p-1.5 rounded-md text-zinc-600 hover:text-rose-400 hover:bg-rose-500/10 opacity-0 group-hover:opacity-100 transition-all duration-200"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
