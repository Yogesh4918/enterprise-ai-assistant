export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'admin' | 'user';
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  confidence_score?: number;
  language?: string;
  created_at: string;
  isStreaming?: boolean;
}

export interface Citation {
  index: number;
  source: string;
  page?: number;
  chunk_text: string;
  relevance_score: number;
}

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  status: 'uploading' | 'processing' | 'indexed' | 'failed';
  language?: string;
  created_at: string;
}

export interface ChatStreamEvent {
  type: 'token' | 'citation' | 'confidence' | 'done' | 'error';
  data: string | Citation | number | { message: string };
}

export interface ConversationGroup {
  label: string;
  conversations: Conversation[];
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  full_name: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token?: string;
  token_type: string;
}
