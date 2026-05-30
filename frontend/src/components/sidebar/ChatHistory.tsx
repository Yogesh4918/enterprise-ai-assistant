"use client";

import React from "react";
import { MessageSquare, Trash2 } from "lucide-react";
import { useChatStore } from "@/stores/chatStore";
import { formatDate, groupConversationsByDate } from "@/lib/utils";
import type { Conversation } from "@/types";

interface ChatHistoryProps {
  searchQuery: string;
}

export function ChatHistory({ searchQuery }: ChatHistoryProps) {
  const { conversations, activeConversationId, selectConversation, deleteConversation, isLoadingConversations } = useChatStore();

  if (isLoadingConversations) {
    return (
      <div className="space-y-2 p-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="skeleton h-10 rounded-lg" style={{ animationDelay: `${i * 100}ms` }} />
        ))}
      </div>
    );
  }

  const filtered = searchQuery
    ? conversations.filter((c) => c.title.toLowerCase().includes(searchQuery.toLowerCase()))
    : conversations;

  const groups = groupConversationsByDate(filtered);

  if (groups.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground text-xs">
        {searchQuery ? "No matching conversations" : "No conversations yet"}
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-4">
      {groups.map((group) => (
        <div key={group.label}>
          <p className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-wider px-2 mb-1">
            {group.label}
          </p>
          <div className="space-y-0.5">
            {group.conversations.map((conv) => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                isActive={conv.id === activeConversationId}
                onSelect={() => selectConversation(conv.id)}
                onDelete={() => deleteConversation(conv.id)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ConversationItem({
  conversation,
  isActive,
  onSelect,
  onDelete,
}: {
  conversation: Conversation;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      onClick={onSelect}
      className={`
        flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer group
        transition-all duration-150
        ${isActive
          ? "bg-brand-purple/15 border border-brand-purple/20 text-foreground"
          : "hover:bg-white/3 text-muted-foreground hover:text-foreground"
        }
      `}
    >
      <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? "text-brand-purple" : ""}`} />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium truncate">{conversation.title}</p>
        <p className="text-[10px] text-muted-foreground/50">{formatDate(conversation.updated_at || conversation.created_at)}</p>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-white/10 text-muted-foreground hover:text-red-400 transition-all"
        title="Delete"
      >
        <Trash2 className="w-3 h-3" />
      </button>
    </div>
  );
}
