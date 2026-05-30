"use client";

import { useCallback, useState } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useAuthStore } from "@/stores/authStore";
import { useWebSocket } from "@/hooks/useWebSocket";
import type { ChatStreamEvent, Citation, Message } from "@/types";
import { generateId } from "@/lib/utils";

export function useChat() {
  const {
    messages,
    activeConversationId,
    isStreaming,
    streamingContent,
    addMessage,
    startStreaming,
    appendStreamingToken,
    finalizeStreamingMessage,
    stopStreaming,
    updateMessageCitations,
    updateMessageConfidence,
    createConversation,
  } = useChatStore();

  const { token } = useAuthStore();
  const [wsStatus, setWsStatus] = useState<string>("disconnected");

  const handleStreamEvent = useCallback(
    (event: ChatStreamEvent) => {
      switch (event.type) {
        case "token":
          appendStreamingToken(event.data as string);
          break;
        case "citation":
          if (useChatStore.getState().streamingMessageId) {
            const currentMsg = useChatStore
              .getState()
              .messages.find(
                (m) => m.id === useChatStore.getState().streamingMessageId
              );
            const citations = [...(currentMsg?.citations || []), event.data as Citation];
            updateMessageCitations(
              useChatStore.getState().streamingMessageId!,
              citations
            );
          }
          break;
        case "confidence":
          if (useChatStore.getState().streamingMessageId) {
            updateMessageConfidence(
              useChatStore.getState().streamingMessageId!,
              event.data as number
            );
          }
          break;
        case "done":
          finalizeStreamingMessage();
          break;
        case "error":
          stopStreaming();
          break;
      }
    },
    [
      appendStreamingToken,
      finalizeStreamingMessage,
      stopStreaming,
      updateMessageCitations,
      updateMessageConfidence,
    ]
  );

  const { send: wsSend } = useWebSocket(
    activeConversationId,
    token,
    handleStreamEvent,
    setWsStatus
  );

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      let convId = activeConversationId;

      // Create conversation if none is active
      if (!convId) {
        try {
          const conv = await createConversation(
            content.slice(0, 50).trim() || "New Chat"
          );
          convId = conv.id;
        } catch {
          return;
        }
      }

      // Add user message to store
      const userMessage: Message = {
        id: generateId(),
        conversation_id: convId,
        role: "user",
        content: content.trim(),
        created_at: new Date().toISOString(),
      };
      addMessage(userMessage);

      // Create placeholder assistant message
      const assistantMessageId = generateId();
      const assistantMessage: Message = {
        id: assistantMessageId,
        conversation_id: convId,
        role: "assistant",
        content: "",
        created_at: new Date().toISOString(),
        isStreaming: true,
      };
      addMessage(assistantMessage);
      startStreaming(assistantMessageId);

      // Send via WebSocket
      wsSend(content.trim());
    },
    [activeConversationId, addMessage, createConversation, startStreaming, wsSend]
  );

  return {
    messages,
    isStreaming,
    streamingContent,
    sendMessage,
    wsStatus,
  };
}
