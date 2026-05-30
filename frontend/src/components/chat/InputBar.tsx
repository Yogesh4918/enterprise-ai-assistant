"use client";

import React, { useRef, useEffect, useState, useCallback } from "react";
import { Send, Paperclip, Mic } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useChat } from "@/hooks/useChat";
import { VoiceInput } from "@/components/voice/VoiceInput";

export function InputBar() {
  const [input, setInput] = useState("");
  const [showVoice, setShowVoice] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { sendMessage, isStreaming } = useChat();

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 180) + "px";
    }
  }, [input]);

  const handleSubmit = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    setInput("");
    await sendMessage(trimmed);
  }, [input, isStreaming, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleVoiceTranscript = (text: string) => {
    setInput((prev) => prev + text);
    setShowVoice(false);
  };

  return (
    <div className="border-t border-border/50 p-4 md:px-8 lg:px-16 xl:px-24">
      <div className="max-w-3xl mx-auto">
        <div className="glass-input rounded-2xl flex items-end gap-2 p-3 transition-all duration-200 focus-within:border-brand-purple/40 focus-within:shadow-[0_0_20px_rgba(124,58,237,0.1)]">
          {/* File upload button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex-shrink-0 p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
            title="Attach file"
          >
            <Paperclip className="w-5 h-5" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            className="hidden"
            onChange={() => {/* handled by document upload flow */}}
          />

          {/* Text input */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Send a message..."
            rows={1}
            className="flex-1 bg-transparent border-none outline-none resize-none text-sm text-foreground placeholder:text-muted-foreground min-h-[24px] max-h-[180px] py-1.5 focus-ring"
            disabled={isStreaming}
          />

          {/* Voice input */}
          {showVoice ? (
            <VoiceInput
              onTranscript={handleVoiceTranscript}
              onCancel={() => setShowVoice(false)}
            />
          ) : (
            <button
              onClick={() => setShowVoice(true)}
              className="flex-shrink-0 p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
              title="Voice input"
            >
              <Mic className="w-5 h-5" />
            </button>
          )}

          {/* Send button */}
          <Button
            onClick={handleSubmit}
            disabled={!input.trim() || isStreaming}
            size="icon"
            className="flex-shrink-0 w-9 h-9 rounded-xl gradient-purple hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200"
          >
            <Send className="w-4 h-4 text-white" />
          </Button>
        </div>

        <p className="text-center text-xs text-muted-foreground/50 mt-2">
          AI can make mistakes. Verify important information with source citations.
        </p>
      </div>
    </div>
  );
}
