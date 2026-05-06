// API Types for Phase 7 Backend Integration

export interface Thread {
  thread_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  metadata?: Record<string, any>;
}

export interface Message {
  id: string;
  thread_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  citation_url?: string;
  metadata?: Record<string, any>;
}

export interface MessageHistory {
  messages: Message[];
  total_count: number;
  has_more: boolean;
}

export interface ThreadCreateRequest {
  metadata?: Record<string, any>;
}

export interface MessageCreateRequest {
  user_message: string;
  context?: Record<string, any>;
}

export interface AssistantResponse {
  assistant_message: string;
  citation_url?: string;
  last_updated: string;
  thread_id: string;
  message_id: string;
  processing_time_ms?: number;
}

export interface HealthResponse {
  status: 'healthy' | 'unhealthy' | 'degraded';
  timestamp: string;
  version: string;
  components?: Record<string, string>;
  uptime_seconds?: number;
}

export interface ErrorResponse {
  error: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}

export interface StatsResponse {
  total_threads: number;
  active_threads: number;
  total_messages: number;
  average_messages_per_thread: number;
  uptime_seconds: number;
  requests_processed: number;
  average_response_time_ms?: number;
}
