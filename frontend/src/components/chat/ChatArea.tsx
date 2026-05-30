"use client";

import React, { useRef, useEffect } from "react";
import { useChatStore } from "@/stores/chatStore";
import { MessageBubble } from "./MessageBubble";
import { Sparkles, MessageSquare } from "lucide-react";

const SUGGESTIONS = [
  "Summarize my uploaded documents",
  "What are the key findings in the report?",
  "Compare the main topics across all documents",
  "Translate the summary into Spanish",
];

export function ChatArea() {
  const { messages, isStreaming, streamingContent, streamingMessageId, activeConversationId, isLoadingMessages } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  if (!activeConversationId) {
    return <WelcomeScreen />;
  }

  if (isLoadingMessages) {
    return (
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="animate-fade-in" style={{ animationDelay: `${i * 100}ms` }}>
            <div className="skeleton h-16 w-3/4 mb-3" />
            <div className="skeleton h-24 w-full" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8 lg:px-16 xl:px-24">
      <div className="max-w-3xl mx-auto space-y-6">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            isCurrentlyStreaming={isStreaming && msg.id === streamingMessageId}
            streamingContent={msg.id === streamingMessageId ? streamingContent : undefined}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function WelcomeScreen() {
  const { createConversation } = useChatStore();

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-2xl w-full text-center animate-fade-in-up">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-purple mb-6 animate-pulse-glow">
          <Sparkles className="w-8 h-8 text-white" />
        </div>

        <h1 className="text-3xl font-bold mb-3 gradient-text">Enterprise AI Assistant</h1>
        <p className="text-muted-foreground text-lg mb-10">
          Upload documents and ask questions. I&apos;ll search, analyze, and cite sources for you.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {SUGGESTIONS.map((suggestion, i) => (
            <button
              key={i}
              onClick={async () => {
                await createConversation(suggestion.slice(0, 40));
              }}
              className="glass-card p-4 text-left text-sm text-muted-foreground hover:text-foreground hover:border-brand-purple/30 transition-all duration-200 cursor-pointer group"
            >
              <MessageSquare className="w-4 h-4 mb-2 text-brand-purple opacity-60 group-hover:opacity-100 transition-opacity" />
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
