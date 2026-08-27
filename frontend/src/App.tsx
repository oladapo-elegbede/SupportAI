import React, { useState } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { KBManagement } from './components/KBManagement'
import { ChatInterface } from './components/ChatInterface'

const DashboardContent: React.FC = () => {
  const { user, logout } = useAuth()
  const [activeTab, setActiveTab] = useState<'kb' | 'chat'>('kb')

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      {/* Navbar */}
      <header className="bg-slate-800 border-b border-slate-700/80 px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-6">
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <span className="text-indigo-400">SupportAI</span> SaaS
          </h1>

          {/* Navigation Tabs */}
          <nav className="flex bg-slate-900 p-1 rounded-lg border border-slate-700/60">
            <button
              onClick={() => setActiveTab('kb')}
              className={`px-4 py-1.5 rounded-md text-xs font-semibold transition ${
                activeTab === 'kb' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Knowledge Bases & Documents
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-4 py-1.5 rounded-md text-xs font-semibold transition ${
                activeTab === 'chat' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              RAG Chat Tester
            </button>
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-xs font-medium text-slate-200">{user?.email}</p>
            <p className="text-[10px] text-slate-400 font-mono">
              {user?.organization?.name} ({user?.role})
            </p>
          </div>
          <button
            onClick={logout}
            className="px-3.5 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 hover:text-white rounded-lg text-xs font-medium transition"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 p-8 max-w-6xl mx-auto w-full">
        {activeTab === 'kb' ? <KBManagement /> : <ChatInterface />}
      </main>
    </div>
  )
}

const MainApp: React.FC = () => {
  const [authView, setAuthView] = useState<'login' | 'register'>('login')

  return (
    <ProtectedRoute
      fallback={
        authView === 'login' ? (
          <LoginPage onSwitchToRegister={() => setAuthView('register')} />
        ) : (
          <RegisterPage onSwitchToLogin={() => setAuthView('login')} />
        )
      }
    >
      <DashboardContent />
    </ProtectedRoute>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  )
}
