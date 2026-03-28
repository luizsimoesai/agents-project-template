// Tipos espelhados dos schemas do backend (backend/src/schemas/)

export interface UserRead {
  id: string
  name: string | null
  email: string
  is_admin: boolean
  is_active: boolean
  created_at: string
}

export interface UserCreate {
  name: string
  email: string
  password: string
}

export interface UserUpdate {
  name?: string
  email?: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number  // seconds until the access_token expires
}

export interface AssistantRead {
  assistant_id: string
  name: string
  description: string | null
  graph_id: string
  config: Record<string, unknown>
  context: Record<string, unknown>
  metadata: Record<string, unknown>
  version: number
  created_at: string
  updated_at: string
}

export interface AssistantCreate {
  name: string
  description?: string
  graph_id?: string
  config?: Record<string, unknown>
  context?: Record<string, unknown>
  metadata?: Record<string, unknown>
}

export interface AssistantUpdate {
  name?: string
  description?: string
  config?: Record<string, unknown>
  context?: Record<string, unknown>
  metadata?: Record<string, unknown>
}

export interface ThreadRead {
  thread_id: string
  status: "idle" | "busy" | "interrupted" | "error"
  assistant_id: string | null
  thread_name: string | null
  created_at: string
  updated_at: string
}

export interface ThreadCreate {
  assistant_id: string
  thread_name?: string
}

export interface MessageRead {
  role: string
  content: string
}

export interface ChatResponse {
  thread_id: string
  message: string
  role: string
}

export interface ApiError {
  detail: string | { msg: string; type: string }[]
}
