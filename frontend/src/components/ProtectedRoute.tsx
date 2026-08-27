import React from 'react'
import { useAuth } from '../context/AuthContext'

interface ProtectedRouteProps {
  children: React.ReactNode
  fallback: React.ReactNode
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  fallback,
}) => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 text-slate-100 flex justify-center items-center p-6">
        <div className="flex items-center gap-3 bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-xl">
          <div className="w-5 h-5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm font-medium text-slate-300">Authenticating session...</span>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <>{fallback}</>
  }

  return <>{children}</>
}
