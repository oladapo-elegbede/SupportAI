import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from 'react'
import type { User, LoginPayload, RegisterPayload } from '../types/auth'
import { authApi } from '../api/auth'

interface AuthContextType {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (payload: LoginPayload) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  logout: () => Promise<void>
  clearError: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const clearError = useCallback(() => setError(null), [])

  // Silent Refresh on App Mount
  useEffect(() => {
    let isMounted = true

    async function initAuth() {
      try {
        const tokenRes = await authApi.refresh()
        if (!isMounted) return

        setAccessToken(tokenRes.access_token)

        const userData = await authApi.getMe(tokenRes.access_token)
        if (!isMounted) return

        setUser(userData)
      } catch {
        if (isMounted) {
          setAccessToken(null)
          setUser(null)
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    initAuth()

    return () => {
      isMounted = false
    }
  }, [])

  const login = async (payload: LoginPayload) => {
    setError(null)
    setIsLoading(true)
    try {
      const tokenRes = await authApi.login(payload)
      setAccessToken(tokenRes.access_token)

      const userData = await authApi.getMe(tokenRes.access_token)
      setUser(userData)
    } catch (err: any) {
      setError(err.message || 'Failed to log in')
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (payload: RegisterPayload) => {
    setError(null)
    setIsLoading(true)
    try {
      await authApi.register(payload)

      const tokenRes = await authApi.login({
        email: payload.email,
        password: payload.password,
      })
      setAccessToken(tokenRes.access_token)

      const userData = await authApi.getMe(tokenRes.access_token)
      setUser(userData)
    } catch (err: any) {
      setError(err.message || 'Registration failed')
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    setIsLoading(true)
    try {
      await authApi.logout()
    } catch {
      // Ignore network errors on logout
    } finally {
      setAccessToken(null)
      setUser(null)
      setError(null)
      setIsLoading(false)
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        accessToken,
        isAuthenticated: !!user && !!accessToken,
        isLoading,
        error,
        login,
        register,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
