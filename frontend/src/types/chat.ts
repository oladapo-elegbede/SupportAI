export interface ChatMessageRequest {
  message: string
  session_id?: string
}

export interface SourceCitation {
  document_name: string
  page_number: int
  similarity_score: number
}

export interface MessageResponse {
  id: string
  conversation_id: string
  sender_type: 'user' | 'assistant' | 'system'
  content: string
  sources?: Array<{
    document_name: string
    page_number: number
    similarity_score: number
  }> | null
  created_at: string
}

export interface ChatMessageResponse {
  conversation_id: string
  session_id: string
  message: MessageResponse
  sources: SourceCitation[]
}

export interface ConversationResponse {
  id: string
  organization_id: string
  knowledge_base_id: string
  session_id: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
}
