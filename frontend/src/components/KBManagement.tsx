import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import { kbApi } from '../api/kb'
import type { KnowledgeBase, Document } from '../types/kb'

export const KBManagement: React.FC = () => {
  const { accessToken } = useAuth()
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  
  const [kbName, setKbName] = useState('')
  const [kbDescription, setKbDescription] = useState('')
  const [isCreatingKb, setIsCreatingKb] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Fetch KBs
  const loadKbs = useCallback(async () => {
    if (!accessToken) return
    try {
      const data = await kbApi.listKbs(accessToken)
      setKbs(data)
      if (data.length > 0 && !selectedKb) {
        setSelectedKb(data[0])
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load Knowledge Bases')
    }
  }, [accessToken, selectedKb])

  // Fetch Documents for Selected KB
  const loadDocuments = useCallback(async () => {
    if (!accessToken || !selectedKb) return
    try {
      const data = await kbApi.listDocuments(accessToken, selectedKb.id)
      setDocuments(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load documents')
    }
  }, [accessToken, selectedKb])

  useEffect(() => {
    loadKbs()
  }, [loadKbs])

  useEffect(() => {
    if (selectedKb) {
      loadDocuments()
    }
  }, [selectedKb, loadDocuments])

  // Automatic Ingestion Status Polling (Polls every 2 seconds if any document is processing)
  useEffect(() => {
    const hasActiveIngestion = documents.some(
      (d) => d.ingestion_status === 'pending' || d.ingestion_status === 'processing' || d.ingestion_status === 'uploaded'
    )

    if (!hasActiveIngestion || !selectedKb || !accessToken) return

    const timer = setInterval(() => {
      loadDocuments()
      loadKbs()
    }, 2000)

    return () => clearInterval(timer)
  }, [documents, selectedKb, accessToken, loadDocuments, loadKbs])

  // Handle KB Creation
  const handleCreateKb = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!accessToken) return
    setError(null)
    setIsCreatingKb(true)
    try {
      const newKb = await kbApi.createKb(accessToken, {
        name: kbName,
        description: kbDescription,
      })
      setSuccess(`Knowledge Base "${newKb.name}" created!`)
      setKbName('')
      setKbDescription('')
      setSelectedKb(newKb)
      await loadKbs()
    } catch (err: any) {
      setError(err.message || 'Failed to create Knowledge Base')
    } finally {
      setIsCreatingKb(false)
    }
  }

  // Handle KB Deletion
  const handleDeleteKb = async (kbId: string) => {
    if (!accessToken || !window.confirm('Delete this Knowledge Base and all its documents?')) return
    setError(null)
    try {
      await kbApi.deleteKb(accessToken, kbId)
      setSuccess('Knowledge Base deleted successfully')
      setSelectedKb(null)
      await loadKbs()
    } catch (err: any) {
      setError(err.message || 'Failed to delete Knowledge Base')
    }
  }

  // Handle File Upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !accessToken || !selectedKb) return
    setError(null)
    setSuccess(null)
    setIsUploading(true)
    try {
      await kbApi.uploadDocument(accessToken, selectedKb.id, file)
      setSuccess(`Document "${file.name}" uploaded! Background ingestion started.`)
      await loadDocuments()
      await loadKbs()
    } catch (err: any) {
      setError(err.message || 'Failed to upload document')
    } finally {
      setIsUploading(false)
      e.target.value = ''
    }
  }

  // Handle Re-ingestion
  const handleReingest = async (docId: string) => {
    if (!accessToken) return
    setError(null)
    try {
      await kbApi.reingestDocument(accessToken, docId)
      setSuccess('Re-ingestion job enqueued!')
      await loadDocuments()
    } catch (err: any) {
      setError(err.message || 'Failed to re-ingest document')
    }
  }

  // Handle Document Deletion
  const handleDeleteDocument = async (docId: string) => {
    if (!accessToken) return
    setError(null)
    try {
      await kbApi.deleteDocument(accessToken, docId)
      setSuccess('Document deleted successfully')
      await loadDocuments()
      await loadKbs()
    } catch (err: any) {
      setError(err.message || 'Failed to delete document')
    }
  }

  return (
    <div className="space-y-8">
      {/* Alert Messages */}
      {error && (
        <div className="p-4 bg-red-950/60 border border-red-800/60 text-red-300 text-sm rounded-lg flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs text-red-400 font-semibold ml-2">Dismiss</button>
        </div>
      )}
      {success && (
        <div className="p-4 bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 text-sm rounded-lg flex justify-between items-center">
          <span>{success}</span>
          <button onClick={() => setSuccess(null)} className="text-xs text-emerald-400 font-semibold ml-2">Dismiss</button>
        </div>
      )}

      {/* Top Grid: Create KB Form & KB Selector */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Create KB Card */}
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl">
          <h3 className="text-base font-bold text-white mb-4">New Knowledge Base</h3>
          <form onSubmit={handleCreateKb} className="space-y-4">
            <div>
              <label className="block text-xs uppercase font-semibold text-slate-300 mb-1">KB Name</label>
              <input
                type="text"
                required
                value={kbName}
                onChange={(e) => setKbName(e.target.value)}
                placeholder="Product Manuals"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs uppercase font-semibold text-slate-300 mb-1">Description</label>
              <textarea
                value={kbDescription}
                onChange={(e) => setKbDescription(e.target.value)}
                placeholder="Optional notes..."
                rows={2}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <button
              type="submit"
              disabled={isCreatingKb}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2 rounded-lg text-xs transition disabled:opacity-50"
            >
              {isCreatingKb ? 'Creating...' : 'Create Knowledge Base'}
            </button>
          </form>
        </div>

        {/* KB Selection List */}
        <div className="md:col-span-2 bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl">
          <h3 className="text-base font-bold text-white mb-4">Knowledge Bases ({kbs.length})</h3>
          {kbs.length === 0 ? (
            <p className="text-slate-400 text-sm italic">No Knowledge Bases created yet. Create one on the left!</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-60 overflow-y-auto pr-1">
              {kbs.map((kb) => (
                <div
                  key={kb.id}
                  onClick={() => setSelectedKb(kb)}
                  className={`p-4 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
                    selectedKb?.id === kb.id
                      ? 'bg-indigo-950/40 border-indigo-500 text-white'
                      : 'bg-slate-900/50 border-slate-700/60 text-slate-300 hover:border-slate-500'
                  }`}
                >
                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <h4 className="font-semibold text-sm text-white truncate">{kb.name}</h4>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-indigo-400 border border-slate-700">
                        {kb.document_count} docs
                      </span>
                    </div>
                    {kb.description && (
                      <p className="text-slate-400 text-xs line-clamp-2">{kb.description}</p>
                    )}
                  </div>
                  <div className="mt-3 pt-2 border-t border-slate-800 flex justify-between items-center text-[10px] text-slate-500">
                    <span>Created: {new Date(kb.created_at).toLocaleDateString()}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteKb(kb.id)
                      }}
                      className="text-red-400 hover:text-red-300 font-semibold"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Section: Document Upload & List for Selected KB */}
      {selectedKb && (
        <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl space-y-6">
          <div className="flex justify-between items-center border-b border-slate-700 pb-4">
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                Documents in <span className="text-indigo-400">{selectedKb.name}</span>
              </h3>
              <p className="text-slate-400 text-xs mt-0.5">Upload PDF or TXT files ($\le$ 20MB) for RAG vector ingestion</p>
            </div>

            {/* File Upload Button */}
            <label className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-xs font-semibold cursor-pointer transition shadow-lg shadow-indigo-600/20">
              {isUploading ? 'Uploading...' : '+ Upload Document'}
              <input
                type="file"
                accept=".pdf,.txt"
                onChange={handleFileUpload}
                disabled={isUploading}
                className="hidden"
              />
            </label>
          </div>

          {/* Document Table */}
          {documents.length === 0 ? (
            <div className="p-8 text-center bg-slate-900/40 rounded-xl border border-dashed border-slate-700">
              <p className="text-slate-400 text-sm">No documents uploaded to this Knowledge Base yet.</p>
              <p className="text-slate-500 text-xs mt-1">Upload a PDF or TXT file to prepare for AI grounding!</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-700 text-slate-400 uppercase font-semibold">
                    <th className="py-3 px-4">Filename</th>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Size</th>
                    <th className="py-3 px-4">Ingestion Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {documents.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-900/30 transition">
                      <td className="py-3 px-4 font-medium text-slate-200">{doc.filename}</td>
                      <td className="py-3 px-4 font-mono uppercase text-indigo-300">{doc.file_type}</td>
                      <td className="py-3 px-4 font-mono text-slate-400">{(doc.file_size_bytes / 1024).toFixed(1)} KB</td>
                      <td className="py-3 px-4">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase inline-flex items-center gap-1.5 ${
                          doc.ingestion_status === 'completed'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : doc.ingestion_status === 'failed'
                            ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                            : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 animate-pulse'
                        }`}>
                          {(doc.ingestion_status === 'pending' || doc.ingestion_status === 'processing') && (
                            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-ping"></span>
                          )}
                          {doc.ingestion_status === 'completed' && '✓ Searchable'}
                          {doc.ingestion_status === 'pending' && 'Queued in Redis'}
                          {doc.ingestion_status === 'processing' && 'Embedding Vectors...'}
                          {doc.ingestion_status === 'failed' && 'Failed'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-3">
                        {doc.ingestion_status === 'failed' && (
                          <button
                            onClick={() => handleReingest(doc.id)}
                            className="text-indigo-400 hover:text-indigo-300 font-semibold"
                          >
                            Re-try
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteDocument(doc.id)}
                          className="text-red-400 hover:text-red-300 font-semibold"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
