import type { ChatStreamEvent } from "@/types";

type MessageHandler = (event: ChatStreamEvent) => void;
type StatusHandler = (status: "connecting" | "connected" | "disconnected" | "error") => void;

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private conversationId: string | null = null;
  private token: string | null = null;
  private onMessageCallback: MessageHandler | null = null;
  private onStatusCallback: StatusHandler | null = null;
  private intentionalClose = false;

  onMessage(handler: MessageHandler) {
    this.onMessageCallback = handler;
  }

  onStatus(handler: StatusHandler) {
    this.onStatusCallback = handler;
  }

  connect(conversationId: string, token: string) {
    this.conversationId = conversationId;
    this.token = token;
    this.intentionalClose = false;
    this.doConnect();
  }

  private doConnect() {
    if (!this.conversationId || !this.token) return;

    // Clean up any existing connection
    this.cleanupConnection();

    this.onStatusCallback?.("connecting");

    const url = `${WS_BASE}/ws/chat/${this.conversationId}?token=${encodeURIComponent(this.token)}`;

    try {
      this.ws = new WebSocket(url);
    } catch {
      this.onStatusCallback?.("error");
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.onStatusCallback?.("connected");
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Ignore pong responses
        if (data.type === "pong") return;

        this.onMessageCallback?.(data as ChatStreamEvent);
      } catch {
        // Non-JSON message, treat as raw token
        this.onMessageCallback?.({
          type: "token",
          data: event.data,
        });
      }
    };

    this.ws.onclose = (event) => {
      this.stopHeartbeat();
      this.onStatusCallback?.("disconnected");

      if (!this.intentionalClose && event.code !== 1000) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      this.onStatusCallback?.("error");
    };
  }

  send(message: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          type: "message",
          content: message,
        })
      );
    }
  }

  disconnect() {
    this.intentionalClose = true;
    this.cleanupConnection();
    this.onStatusCallback?.("disconnected");
  }

  private cleanupConnection() {
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      if (
        this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING
      ) {
        this.ws.close(1000);
      }
      this.ws = null;
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 30000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.onStatusCallback?.("error");
      return;
    }

    const delay = Math.min(
      1000 * Math.pow(2, this.reconnectAttempts),
      30000
    );
    this.reconnectAttempts++;

    this.reconnectTimer = setTimeout(() => {
      this.doConnect();
    }, delay);
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const wsClient = new WebSocketClient();
export default wsClient;
