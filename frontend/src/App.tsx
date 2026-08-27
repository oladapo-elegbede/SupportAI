import React, { useState } from 'react'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'

const DashboardContent: React.FC = () => {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      <header className="bg-slate-800 border-b border-slate-700/80 px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <span className="text-indigo-400">SupportAI</span> SaaS
          </h1>
          <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            Authenticated
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

      <main className="flex-1 p-8 max-w-4xl mx-auto w-full">
        <div className="bg-slate-800 rounded-xl shadow-2xl p-8 border border-slate-700">
          <h2 className="text-xl font-bold text-white mb-2">
            Welcome, {user?.email}!
          </h2>
          <p className="text-slate-400 text-sm mb-6 leading-relaxed">
            Your tenant organization{' '}
            <strong className="text-indigo-300">{user?.organization?.name}</strong>{' '}
            (Slug: <code className="text-xs bg-slate-900 px-2 py-1 rounded text-emerald-400">{user?.organization?.slug}</code>) is fully provisioned.
          </p>

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-700/50">
              <span className="text-slate-500 block mb-1">User ID</span>
              <span className="font-mono text-slate-300 break-all">{user?.id}</span>
            </div>
            <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-700/50">
              <span className="text-slate-500 block mb-1">Organization ID</span>
              <span className="font-mono text-slate-300 break-all">{user?.organization_id}</span>
            </div>
            <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-700/50">
              <span className="text-slate-500 block mb-1">Role Permission</span>
              <span className="font-mono text-indigo-400 uppercase font-semibold">{user?.role}</span>
            </div>
            <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-700/50">
              <span className="text-slate-500 block mb-1">Session Security</span>
              <span className="font-mono text-emerald-400 font-semibold">httpOnly Cookie Active</span>
            </div>
          </div>
        </div>
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
