import React, { useState } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { KBManagement } from './components/KBManagement'

const DashboardContent: React.FC = () => {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      {/* Navbar */}
      <header className="bg-slate-800 border-b border-slate-700/80 px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <span className="text-indigo-400">SupportAI</span> SaaS
          </h1>
          <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            Phase 3 Active
          </span>
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
        <KBManagement />
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
