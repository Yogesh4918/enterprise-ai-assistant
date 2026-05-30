import type {
  AuthTokens,
  Conversation,
  Document,
  LoginCredentials,
  Message,
  RegisterCredentials,
  User,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private accessToken: string | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.accessToken = localStorage.getItem("access_token");
    }
  }

  setToken(token: string | null) {
    this.accessToken = token;
    if (typeof window !== "undefined") {
      if (token) {
        localStorage.setItem("access_token", token);
      } else {
        localStorage.removeItem("access_token");
      }
    }
  }

  getToken(): string | null {
    return this.accessToken;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (this.accessToken) {
      headers["Authorization"] = `Bearer ${this.accessToken}`;
    }

    // Remove Content-Type for FormData
    if (options.body instanceof FormData) {
      delete headers["Content-Type"];
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401 && this.accessToken) {
      // Try to refresh
      const refreshed = await this.refreshToken();
      if (refreshed) {
        headers["Authorization"] = `Bearer ${this.accessToken}`;
        const retryResponse = await fetch(`${API_BASE}${endpoint}`, {
          ...options,
          headers,
        });
        if (!retryResponse.ok) {
          throw new ApiError(retryResponse.status, await retryResponse.text());
        }
        return retryResponse.json();
      }
      // Refresh failed — clear and throw
      this.setToken(null);
      throw new ApiError(401, "Session expired. Please login again.");
    }

    if (!response.ok) {
      let errorMsg = "Request failed";
      try {
        const errData = await response.json();
        errorMsg = errData.detail || errData.message || errorMsg;
      } catch {
        errorMsg = await response.text();
      }
      throw new ApiError(response.status, errorMsg);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // ─── Auth ──────────────────────────────────────────
  async login(credentials: LoginCredentials): Promise<AuthTokens> {
    const formData = new URLSearchParams();
    formData.append("username", credentials.email);
    formData.append("password", credentials.password);

    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    });

    if (!response.ok) {
      let errorMsg = "Login failed";
      try {
        const errData = await response.json();
        errorMsg = errData.detail || errorMsg;
      } catch {
        errorMsg = await response.text();
      }
      throw new ApiError(response.status, errorMsg);
    }

    const tokens: AuthTokens = await response.json();
    this.setToken(tokens.access_token);
    return tokens;
  }

  async register(credentials: RegisterCredentials): Promise<User> {
    return this.request<User>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(credentials),
    });
  }

  async refreshToken(): Promise<boolean> {
    try {
      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) return false;

      const response = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) return false;

      const tokens: AuthTokens = await response.json();
      this.setToken(tokens.access_token);
      if (tokens.refresh_token) {
        localStorage.setItem("refresh_token", tokens.refresh_token);
      }
      return true;
    } catch {
      return false;
    }
  }

  async getMe(): Promise<User> {
    return this.request<User>("/api/auth/me");
  }

  // ─── Conversations ────────────────────────────────
  async getConversations(): Promise<Conversation[]> {
    return this.request<Conversation[]>("/api/chat");
  }

  async createConversation(title?: string): Promise<Conversation> {
    return this.request<Conversation>("/api/chat", {
      method: "POST",
      body: JSON.stringify({ title: title || "New Chat" }),
    });
  }

  async getConversation(id: string): Promise<Conversation> {
    return this.request<Conversation>(`/api/chat/${id}`);
  }

  async deleteConversation(id: string): Promise<void> {
    return this.request<void>(`/api/chat/${id}`, {
      method: "DELETE",
    });
  }

  async getMessages(conversationId: string): Promise<Message[]> {
    const data = await this.request<{ messages: Message[] }>(
      `/api/chat/${conversationId}`
    );
    return data.messages || [];
  }

  // ─── Documents ────────────────────────────────────
  async uploadDocument(file: File): Promise<Document> {
    const formData = new FormData();
    formData.append("file", file);

    return this.request<Document>("/api/documents/upload", {
      method: "POST",
      body: formData,
    });
  }

  async getDocuments(): Promise<Document[]> {
    return this.request<Document[]>("/api/documents");
  }

  async deleteDocument(id: string): Promise<void> {
    return this.request<void>(`/api/documents/${id}`, {
      method: "DELETE",
    });
  }

  async getDocumentStatus(id: string): Promise<Document> {
    return this.request<Document>(`/api/documents/${id}/status`);
  }

  // ─── Voice ────────────────────────────────────────
  async transcribeAudio(audioBlob: Blob): Promise<{ text: string }> {
    const formData = new FormData();
    formData.append("file", audioBlob, "recording.webm");

    return this.request<{ text: string }>("/api/voice/transcribe", {
      method: "POST",
      body: formData,
    });
  }

  async synthesizeSpeech(text: string): Promise<Blob> {
    const response = await fetch(`${API_BASE}/api/voice/synthesize`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(this.accessToken
          ? { Authorization: `Bearer ${this.accessToken}` }
          : {}),
      },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      throw new ApiError(response.status, "Speech synthesis failed");
    }

    return response.blob();
  }

  // ─── Analytics ─────────────────────────────────────
  async getUsageStats(): Promise<any> {
    return this.request<any>("/api/analytics/usage");
  }

  async getConversationActivity(days: number = 30): Promise<any> {
    return this.request<any>(`/api/analytics/conversations/activity?days=${days}`);
  }

  async getDocumentStats(): Promise<any> {
    return this.request<any>("/api/analytics/documents/stats");
  }
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export const api = new ApiClient();
export default api;
