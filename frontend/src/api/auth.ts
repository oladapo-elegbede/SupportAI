import type {
  User,
  LoginPayload,
  RegisterPayload,
  TokenResponse,
} from '../types/auth'

const API_BASE_URL = 'http://localhost:8000/api/v1'

class ApiRequestError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail = 'An unexpected error occurred'
    try {
      const errorData = await response.json()
      if (typeof errorData.detail === 'string') {
        errorDetail = errorData.detail
      } else if (Array.isArray(errorData.detail)) {
        errorDetail = errorData.detail.map((e: any) => e.msg).join(', ')
      }
    } catch {
      // Failed to parse JSON error
    }
    throw new ApiRequestError(errorDetail, response.status)
  }
  return response.json()
}

export const authApi = {
  async register(payload: RegisterPayload): Promise<User> {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'include',
    })
    return handleResponse<User>(res)
  },

  async login(payload: LoginPayload): Promise<TokenResponse> {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'include',
    })
    return handleResponse<TokenResponse>(res)
  },

  async refresh(): Promise<TokenResponse> {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    })
    return handleResponse<TokenResponse>(res)
  },

  async logout(): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    })
    return handleResponse<{ message: string }>(res)
  },

  async getMe(accessToken: string): Promise<User> {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      credentials: 'include',
    })
    return handleResponse<User>(res)
  },
}
