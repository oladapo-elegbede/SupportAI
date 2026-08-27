import type {
  ChatMessageRequest,
  ChatMessageResponse,
  ConversationResponse,
  MessageResponse,
} from '../types/chat'

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

export const chatApi = {
  // Authenticated Admin RAG Chat
  async sendAdminMessage(
    accessToken: string,
    kbId: string,
    payload: ChatMessageRequest
  ): Promise<ChatMessageResponse> {
    const res = await fetch(`${API_BASE_URL}/knowledge-bases/${kbId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(payload),
      credentials: 'include',
    })
    return handleResponse<ChatMessageResponse>(res)
  },

  // Public Customer RAG Chat (Unauthenticated)
  async sendPublicMessage(
    kbId: string,
    payload: ChatMessageRequest
  ): Promise<ChatMessageResponse> {
    const res = await fetch(`${API_BASE_URL}/public/chat/${kbId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    return handleResponse<ChatMessageResponse>(res)
  },

  // List Admin Conversations
  async listConversations(accessToken: string): Promise<ConversationResponse[]> {
    const res = await fetch(`${API_BASE_URL}/conversations`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      credentials: 'include',
    })
    return handleResponse<ConversationResponse[]>(res)
  },

  // Get Conversation History
  async getMessages(accessToken: string, conversationId: string): Promise<MessageResponse[]> {
    const res = await fetch(`${API_BASE_URL}/conversations/${conversationId}/messages`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      credentials: 'include',
    })
    return handleResponse<MessageResponse[]>(res)
  },
}
