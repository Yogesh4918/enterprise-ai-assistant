"use client";

import { create } from "zustand";
import type { Conversation, Message } from "@/types";
import api from "@/lib/api";

interface ChatState {
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  streamingMessageId: string | null;
  isLoadingConversations: boolean;
  isLoadingMessages: boolean;

  // Conversation actions
  loadConversations: () => Promise<void>;
  selectConversation: (id: string | null) => Promise<void>;
  createConversation: (title?: string) => Promise<Conversation>;
  deleteConversation: (id: string) => Promise<void>;
  setConversations: (conversations: Conversation[]) => void;

  // Message actions
  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  updateStreamingContent: (content: string) => void;
  appendStreamingToken: (token: string) => void;
  startStreaming: (messageId: string) => void;
  stopStreaming: () => void;
  updateMessageCitations: (messageId: string, citations: Message["citations"]) => void;
  updateMessageConfidence: (messageId: string, score: number) => void;
  finalizeStreamingMessage: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  messages: [],
  isStreaming: false,
  streamingContent: "",
  streamingMessageId: null,
  isLoadingConversations: false,
  isLoadingMessages: false,

  loadConversations: async () => {
    set({ isLoadingConversations: true });
    try {
      const conversations = await api.getConversations();
      set({ conversations, isLoadingConversations: false });
    } catch {
      set({ isLoadingConversations: false });
    }
  },

  selectConversation: async (id: string | null) => {
    if (id === get().activeConversationId) return;
    set({ activeConversationId: id, messages: [], isLoadingMessages: !!id });

    if (id) {
      try {
        const messages = await api.getMessages(id);
        set({ messages, isLoadingMessages: false });
      } catch {
        set({ isLoadingMessages: false });
      }
    }
  },

  createConversation: async (title?: string) => {
    const conversation = await api.createConversation(title);
    set((state) => ({
      conversations: [conversation, ...state.conversations],
      activeConversationId: conversation.id,
      messages: [],
    }));
    return conversation;
  },

  deleteConversation: async (id: string) => {
    await api.deleteConversation(id);
    set((state) => {
      const conversations = state.conversations.filter((c) => c.id !== id);
      const activeConversationId =
        state.activeConversationId === id ? null : state.activeConversationId;
      return {
        conversations,
        activeConversationId,
        messages: activeConversationId ? state.messages : [],
      };
    });
  },

  setConversations: (conversations) => set({ conversations }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  setMessages: (messages) => set({ messages }),

  updateStreamingContent: (content) => set({ streamingContent: content }),

  appendStreamingToken: (token) =>
    set((state) => ({
      streamingContent: state.streamingContent + token,
    })),

  startStreaming: (messageId) =>
    set({
      isStreaming: true,
      streamingContent: "",
      streamingMessageId: messageId,
    }),

  stopStreaming: () =>
    set({
      isStreaming: false,
      streamingContent: "",
      streamingMessageId: null,
    }),

  updateMessageCitations: (messageId, citations) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, citations } : m
      ),
    })),

  updateMessageConfidence: (messageId, score) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId ? { ...m, confidence_score: score } : m
      ),
    })),

  finalizeStreamingMessage: () => {
    const { streamingContent, streamingMessageId, messages } = get();
    if (!streamingMessageId) return;

    set({
      messages: messages.map((m) =>
        m.id === streamingMessageId
          ? { ...m, content: streamingContent, isStreaming: false }
          : m
      ),
      isStreaming: false,
      streamingContent: "",
      streamingMessageId: null,
    });
  },
}));
