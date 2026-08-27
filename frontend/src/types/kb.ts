export interface KnowledgeBase {
  id: string
  organization_id: string
  name: string
  description?: string | null
  document_count: number
  created_at: string
  updated_at: string
}

export interface KnowledgeBaseCreate {
  name: string
  description?: string
}

export interface Document {
  id: string
  organization_id: string
  knowledge_base_id: string
  filename: string
  file_path: string
  file_type: string
  file_size_bytes: number
  ingestion_status: 'uploaded' | 'pending' | 'processing' | 'completed' | 'failed'
  ingestion_version: number
  error_message?: string | null
  created_at: string
  updated_at: string
}
