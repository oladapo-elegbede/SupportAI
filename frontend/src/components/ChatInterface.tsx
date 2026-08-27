import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'
import { chatApi } from '../api/chat'
import { kbApi } from '../api/kb'
import type { KnowledgeBase } from '../types/kb'

interface ChatMessage {
  id: string
  sender: 'user' | 'assistant'
  content: string
  sources?: Array<{ document_name: string; page_number: number; similarity_score: number }>
  timestamp: string
}

export const ChatInterface: React.FC = () => {
  const { accessToken } = useAuth()
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null)
  
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [sessionId, setSessionId] = useState<string>('')
  const [isSending, setIsSending] = useState(false)
  const [isPublicMode, setIsPublicMode] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Load KBs on mount
  const loadKbs = useCallback(async () => {
    if (!accessToken) return
    try {
      const data = await kbApi.listKbs(accessToken)
      setKbs(data)
      if (data.length > 0 && !selectedKb) {
        setSelectedKb(data[0]) // Select first KB by default
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load Knowledge Bases')
    }
  }, [accessToken, selectedKb])

  useEffect(() => {
    loadKbs()
  }, [loadKbs])

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isSending])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputMessage.trim() || !selectedKb || isSending) return

    const userQuery = inputMessage.trim()
    setInputMessage('')
    setError(null)
    setIsSending(true)

    // Append User Message
    const tempUserMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      sender: 'user',
      content: userQuery,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }
    setMessages((prev) => [...prev, tempUserMsg])

    try {
      let resp
      if (isPublicMode) {
        resp = await chatApi.sendPublicMessage(selectedKb.id, {
          message: userQuery,
          session_id: sessionId || undefined,
        })
      } else {
        if (!accessToken) throw new Error('Not authenticated')
        resp = await chatApi.sendAdminMessage(accessToken, selectedKb.id, {
          message: userQuery,
          session_id: sessionId || undefined,
        })
      }

      if (!sessionId) {
        setSessionId(resp.session_id)
      }

      const assistantMsg: ChatMessage = {
        id: resp.message.id,
        sender: 'assistant',
        content: resp.message.content,
        sources: resp.sources,
        timestamp: new Date(resp.message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err: any) {
      setError(err.message || 'Failed to generate AI response')
    } finally {
      setIsSending(false)
    }
  }

  const handleResetSession = () => {
    setMessages([])
    setSessionId('')
    setError(null)
  }

  return (
    <div className="bg-slate-800 rounded-xl border border-slate-700 shadow-2xl flex flex-col h-[650px] overflow-hidden">
      {/* Header */}
      <div className="bg-slate-800/90 border-b border-slate-700 px-6 py-4 flex flex-wrap justify-between items-center gap-4">
        <div className="flex items-center gap-3">
          <h3 className="text-base font-bold text-white">AI Agent:</h3>
          {/* KB Dropdown Selector */}
          <select
            value={selectedKb?.id || ''}
            onChange={(e) => {
              const kb = kbs.find((k) => k.id === e.target.value)
              if (kb) {
                setSelectedKb(kb)
                handleResetSession()
              }
            }}
            className="bg-slate-900 border border-slate-700 text-indigo-300 rounded-lg px-3 py-1.5 text-xs font-semibold focus:outline-none focus:border-indigo-500"
          >
            {kbs.map((kb) => (
              <option key={kb.id} value={kb.id}>
                {kb.name} ({kb.document_count} docs)
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={isPublicMode}
              onChange={(e) => {
                setIsPublicMode(e.target.checked)
                handleResetSession()
              }}
              className="rounded bg-slate-900 border-slate-700 text-indigo-500 focus:ring-0"
            />
            <span className={isPublicMode ? 'text-emerald-400 font-semibold' : 'text-slate-400'}>
              {isPublicMode ? 'Public Widget Mode' : 'Admin Tester Mode'}
            </span>
          </label>

          <button
            onClick={handleResetSession}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-white rounded text-xs font-medium transition"
          >
            New Session
          </button>
        </div>
      </div>

      {/* Message Feed */}
      <div className="flex-1 p-6 overflow-y-auto space-y-4 bg-slate-900/40">
        {error && (
          <div className="p-3 bg-red-950/60 border border-red-800/60 text-red-300 text-xs rounded-lg flex justify-between items-center">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="font-semibold text-red-400 ml-2">Dismiss</button>
          </div>
        )}

        {messages.length === 0 && (
          <div className="h-full flex flex-col justify-center items-center text-center p-6 text-slate-500">
            <p className="text-sm font-medium">Ask a question to test RAG response grounding!</p>
            <p className="text-xs mt-1">
              Answers will be generated using only documents in "{selectedKb?.name || 'Selected Knowledge Base'}"
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-2xl px-4 py-3 rounded-xl text-sm leading-relaxed ${
                msg.sender === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-none shadow-lg shadow-indigo-600/10'
                  : 'bg-slate-800 text-slate-100 border border-slate-700/80 rounded-bl-none shadow-xl'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>

              {/* Source Citation Cards */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-700/60 space-y-1">
                  <span className="text-[10px] uppercase font-semibold text-indigo-400 tracking-wider block">
                    Verified Documentation Sources:
                  </span>
                  {msg.sources.map((s, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-xs text-slate-300 font-mono bg-slate-900/60 px-2.5 py-1 rounded border border-slate-700/50">
                      <span>📄 {s.document_name}</span>
                      <span className="text-slate-500">|</span>
                      <span>Page {s.page_number}</span>
                      <span className="text-slate-500">|</span>
                      <span className="text-emerald-400">Match: {(s.similarity_score * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <span className="text-[10px] text-slate-500 mt-1 px-1">{msg.timestamp}</span>
          </div>
        ))}

        {isSending && (
          <div className="flex items-start">
            <div className="bg-slate-800 border border-slate-700/80 px-4 py-3 rounded-xl rounded-bl-none flex items-center gap-3">
              <div className="w-4 h-4 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-xs text-slate-400 font-medium">
                Searching vector embeddings & generating answer...
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <form onSubmit={handleSendMessage} className="p-4 bg-slate-800 border-t border-slate-700 flex gap-3">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder={`Ask anything about ${selectedKb?.name || 'documentation'}...`}
          disabled={isSending || !selectedKb}
          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!inputMessage.trim() || isSending || !selectedKb}
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-6 py-2.5 rounded-lg text-sm transition shadow-lg shadow-indigo-600/20 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  )
}
