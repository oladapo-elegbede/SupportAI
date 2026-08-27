export interface Organization {
  id: string
  name: string
  slug: string
  created_at: string
  updated_at: string
}

export interface User {
  id: string
  organization_id: string
  email: string
  first_name?: string | null
  last_name?: string | null
  role: 'owner' | 'member'
  is_active: boolean
  created_at: string
  updated_at: string
  organization?: Organization | null
}

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  email: string
  password: string
  company_name: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface ApiError {
  detail: string
}
