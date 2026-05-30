"use client";

import React, { useState } from "react";
import type { Message } from "@/types";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Sparkles, Copy, Check, ThumbsUp, ThumbsDown, RotateCcw } from "lucide-react";
import { Citations } from "./Citations";
import { ConfidenceScore } from "./ConfidenceScore";

interface MessageBubbleProps {
  message: Message;
  isCurrentlyStreaming?: boolean;
  streamingContent?: string;
}

export function MessageBubble({ message, isCurrentlyStreaming, streamingContent }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const isUser = message.role === "user";
  const displayContent = isCurrentlyStreaming ? (streamingContent || "") : message.content;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(displayContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex gap-3 animate-fade-in ${isUser ? "justify-end" : "justify-start"}`}>
      {/* Avatar */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg gradient-purple flex items-center justify-center mt-1">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
      )}

      <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[80%] group`}>
        {/* Message bubble */}
        <div className={isUser ? "message-user px-4 py-3" : "message-assistant px-4 py-3"}>
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{displayContent}</p>
          ) : (
            <div className="prose-chat text-sm">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    const isBlock = String(children).includes("\n");
                    if (isBlock) {
                      return (
                        <div className="relative">
                          {match && (
                            <div className="absolute top-2 right-2 text-xs text-muted-foreground px-2 py-0.5 rounded bg-black/30">
                              {match[1]}
                            </div>
                          )}
                          <pre className={className}><code {...props}>{children}</code></pre>
                        </div>
                      );
                    }
                    return <code className={className} {...props}>{children}</code>;
                  },
                }}
              >
                {displayContent}
              </ReactMarkdown>
              {isCurrentlyStreaming && (
                <span className="inline-block w-2 h-5 bg-brand-purple ml-0.5 animate-blink rounded-sm" />
              )}
            </div>
          )}
        </div>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <Citations citations={message.citations} />
        )}

        {/* Confidence Score */}
        {!isUser && message.confidence_score != null && !isCurrentlyStreaming && (
          <ConfidenceScore score={message.confidence_score} />
        )}

        {/* Action buttons */}
        {!isUser && !isCurrentlyStreaming && displayContent && (
          <div className="flex items-center gap-1 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-md hover:bg-white/5 text-muted-foreground hover:text-foreground transition-colors"
              title="Copy"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
            <button
              onClick={() => setFeedback("up")}
              className={`p-1.5 rounded-md hover:bg-white/5 transition-colors ${feedback === "up" ? "text-green-400" : "text-muted-foreground hover:text-foreground"}`}
              title="Good response"
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setFeedback("down")}
              className={`p-1.5 rounded-md hover:bg-white/5 transition-colors ${feedback === "down" ? "text-red-400" : "text-muted-foreground hover:text-foreground"}`}
              title="Bad response"
            >
              <ThumbsDown className="w-3.5 h-3.5" />
            </button>
            <button
              className="p-1.5 rounded-md hover:bg-white/5 text-muted-foreground hover:text-foreground transition-colors"
              title="Regenerate"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-brand-purple/20 border border-brand-purple/30 flex items-center justify-center mt-1">
          <User className="w-4 h-4 text-brand-purple" />
        </div>
      )}
    </div>
  );
}
