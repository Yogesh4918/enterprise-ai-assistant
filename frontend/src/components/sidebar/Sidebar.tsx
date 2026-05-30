"use client";

import React, { useEffect, useState } from "react";
import { Plus, Search, PanelLeftClose, PanelLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useChatStore } from "@/stores/chatStore";
import { ChatHistory } from "./ChatHistory";
import { UserMenu } from "./UserMenu";

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

export function Sidebar({ isOpen, onToggle }: SidebarProps) {
  const { createConversation, loadConversations } = useChatStore();
  const [search, setSearch] = useState("");

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const handleNewChat = async () => {
    await createConversation("New Chat");
  };

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 z-30 md:hidden" onClick={onToggle} />
      )}

      {/* Toggle button when closed */}
      {!isOpen && (
        <button
          onClick={onToggle}
          className="fixed top-4 left-4 z-20 p-2 rounded-lg glass hover:bg-white/5 transition-colors"
        >
          <PanelLeft className="w-5 h-5 text-muted-foreground" />
        </button>
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed md:relative z-40 h-full flex flex-col w-[280px]
          glass-sidebar transition-transform duration-300 ease-in-out
          ${isOpen ? "translate-x-0" : "-translate-x-full md:-translate-x-full"}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/5">
          <h2 className="text-sm font-semibold gradient-text">AI Assistant</h2>
          <button
            onClick={onToggle}
            className="p-1.5 rounded-lg hover:bg-white/5 text-muted-foreground hover:text-foreground transition-colors"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <Button
            onClick={handleNewChat}
            className="w-full gradient-purple hover:opacity-90 text-white rounded-xl h-10 text-sm font-medium transition-all duration-200"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Chat
          </Button>
        </div>

        {/* Search */}
        <div className="px-3 pb-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search conversations..."
              className="w-full bg-white/3 border border-white/5 rounded-lg pl-9 pr-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/60 outline-none focus:border-brand-purple/40 transition-colors"
            />
          </div>
        </div>

        {/* Chat History */}
        <ScrollArea className="flex-1 px-2">
          <ChatHistory searchQuery={search} />
        </ScrollArea>

        {/* User Menu */}
        <UserMenu />
      </aside>
    </>
  );
}
