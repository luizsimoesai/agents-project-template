// Types mirrored from backend schemas (backend/src/schemas/)

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

export interface ModelRead {
  id: string
  display_name: string
  model_id: string
  provider: string
  description: string | null
  base_url: string | null
  is_active: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface ModelCreate {
  display_name: string
  model_id: string
  provider: string
  description?: string
  base_url?: string
  is_active?: boolean
  is_default?: boolean
}

export interface ModelUpdate {
  display_name?: string
  description?: string
  base_url?: string
  is_active?: boolean
  is_default?: boolean
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
  metadata: {
    // assistant_id is reserved by Aegra (tracks last-used assistant after runs).
    // thread_assistant_id is our custom key set at creation time.
    assistant_id?: string | null
    thread_assistant_id?: string
    thread_name?: string
    thread_model?: string
    thread_model_base_url?: string | null
    owner?: string
    [key: string]: unknown
  }
  created_at: string
  updated_at: string
}

export interface ThreadCreate {
  assistant_id: string
  thread_name?: string
}

export interface ApiError {
  detail: string | { msg: string; type: string }[]
}
