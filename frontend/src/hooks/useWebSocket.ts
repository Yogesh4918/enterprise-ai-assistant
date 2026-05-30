"use client";

import { useEffect, useRef, useCallback } from "react";
import { WebSocketClient } from "@/lib/websocket";
import type { ChatStreamEvent } from "@/types";

type StatusType = "connecting" | "connected" | "disconnected" | "error";

export function useWebSocket(
  conversationId: string | null,
  token: string | null,
  onMessage: (event: ChatStreamEvent) => void,
  onStatus?: (status: StatusType) => void
) {
  const wsRef = useRef<WebSocketClient | null>(null);
  const onMessageRef = useRef(onMessage);
  const onStatusRef = useRef(onStatus);

  // Keep refs up to date
  onMessageRef.current = onMessage;
  onStatusRef.current = onStatus;

  useEffect(() => {
    if (!conversationId || !token) {
      wsRef.current?.disconnect();
      wsRef.current = null;
      return;
    }

    const client = new WebSocketClient();
    wsRef.current = client;

    client.onMessage((event) => {
      onMessageRef.current(event);
    });

    client.onStatus((status) => {
      onStatusRef.current?.(status);
    });

    client.connect(conversationId, token);

    return () => {
      client.disconnect();
      wsRef.current = null;
    };
  }, [conversationId, token]);

  const send = useCallback((message: string) => {
    wsRef.current?.send(message);
  }, []);

  const isConnected = wsRef.current?.isConnected ?? false;

  return { send, isConnected };
}
