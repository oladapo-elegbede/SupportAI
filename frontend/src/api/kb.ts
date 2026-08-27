import type {
  KnowledgeBase,
  KnowledgeBaseCreate,
  Document,
} from '../types/kb'

const API_BASE_URL = 'http://localhost:8000/api/v1'

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
      // JSON parse error
    }
    throw new Error(errorDetail)
  }
  return response.json()
}

export const kbApi = {
  async listKbs(accessToken: string): Promise<KnowledgeBase[]> {
    const res = await fetch(`${API_BASE_URL}/knowledge-bases`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      credentials: 'include',
    })
    return handleResponse<KnowledgeBase[]>(res)
  },

  async createKb(accessToken: string, payload: KnowledgeBaseCreate): Promise<KnowledgeBase> {
    const res = await fetch(`${API_BASE_URL}/knowledge-bases`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(payload),
      credentials: 'include',
    })
    return handleResponse<KnowledgeBase>(res)
  },

  async deleteKb(accessToken: string, kbId: string): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE_URL}/knowledge-bases/${kbId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      credentials: 'include',
    })
    return handleResponse<{ message: string }>(res)
  },

  async listDocuments(accessToken: string, kbId: string): Promise<Document[]> {
    const res = await fetch(`${API_BASE_URL}/knowledge-bases/${kbId}/documents`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      credentials: 'include',
    })
    return handleResponse<Document[]>(res)
  },

  async uploadDocument(accessToken: string, kbId: string, file: File): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)

    const res = await fetch(`${API_BASE_URL}/knowledge-bases/${kbId}/documents`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      body: formData,
      credentials: 'include',
    })
    return handleResponse<Document>(res)
  },

  async deleteDocument(accessToken: string, docId: string): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE_URL}/documents/${docId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      credentials: 'include',
    })
    return handleResponse<{ message: string }>(res)
  },
}
