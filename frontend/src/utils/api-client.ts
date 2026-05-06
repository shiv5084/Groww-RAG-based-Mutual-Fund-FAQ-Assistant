// Type-safe API client for Phase 7 Backend Integration

import {
  Thread,
  Message,
  MessageHistory,
  ThreadCreateRequest,
  MessageCreateRequest,
  AssistantResponse,
  HealthResponse,
  ErrorResponse,
  StatsResponse,
} from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || (
  typeof window !== 'undefined' && window.location?.hostname === 'localhost' 
    ? `http://localhost:${process.env.NEXT_PUBLIC_BACKEND_PORT || 8000}/api/v1` 
    : '/api/v1'
);

class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public data?: ErrorResponse
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

class ApiClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        let errorData: ErrorResponse;
        try {
          errorData = await response.json();
        } catch {
          errorData = {
            error: 'http_error',
            message: `HTTP ${response.status}: ${response.statusText}`,
            timestamp: new Date().toISOString(),
          };
        }
        throw new ApiError(errorData.message, response.status, errorData);
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(
        error instanceof Error ? error.message : 'Unknown error occurred'
      );
    }
  }

  // Thread Management
  async createThread(request?: ThreadCreateRequest): Promise<Thread> {
    return this.request<Thread>('/threads', {
      method: 'POST',
      body: JSON.stringify(request || {}),
    });
  }

  async getThread(threadId: string): Promise<Thread> {
    return this.request<Thread>(`/threads/${threadId}`);
  }

  async deleteThread(threadId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/threads/${threadId}`, {
      method: 'DELETE',
    });
  }

  async listThreads(limit?: number, offset?: number): Promise<Thread[]> {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());
    
    const query = params.toString();
    return this.request<Thread[]>(`/threads${query ? `?${query}` : ''}`);
  }

  // Message Management
  async sendMessage(
    threadId: string,
    request: MessageCreateRequest
  ): Promise<AssistantResponse> {
    return this.request<AssistantResponse>(`/threads/${threadId}/messages`, {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getMessages(
    threadId: string,
    limit?: number,
    offset?: number
  ): Promise<MessageHistory> {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());
    
    const query = params.toString();
    return this.request<MessageHistory>(
      `/threads/${threadId}/messages${query ? `?${query}` : ''}`
    );
  }

  // System Endpoints
  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  async getStats(): Promise<StatsResponse> {
    return this.request<StatsResponse>('/stats');
  }
}

// Create singleton instance
export const apiClient = new ApiClient();

// Export types and error class
export { ApiError };
export default apiClient;
