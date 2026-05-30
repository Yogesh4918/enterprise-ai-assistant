"use client";

import React from "react";
import { LogOut, User, FileText, BarChart3 } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuthStore } from "@/stores/authStore";
import Link from "next/link";

export function UserMenu() {
  const { user, logout } = useAuthStore();

  const initials = user?.full_name
    ? user.full_name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() || "U";

  return (
    <div className="border-t border-white/5 p-3 space-y-1">
      <Link
        href="/documents"
        className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-muted-foreground hover:text-foreground hover:bg-white/3 transition-colors"
      >
        <FileText className="w-4 h-4" />
        Documents
      </Link>

      <Link
        href="/analytics"
        className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-muted-foreground hover:text-foreground hover:bg-white/3 transition-colors"
      >
        <BarChart3 className="w-4 h-4" />
        Analytics
      </Link>

      <div className="flex items-center gap-2.5 px-3 py-2">
        <Avatar className="w-7 h-7">
          <AvatarFallback className="bg-brand-purple/20 text-brand-purple text-xs font-medium">
            {initials}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium truncate">{user?.full_name || "User"}</p>
          <p className="text-[10px] text-muted-foreground truncate">{user?.email}</p>
        </div>
        <button
          onClick={logout}
          className="p-1.5 rounded-lg hover:bg-white/5 text-muted-foreground hover:text-red-400 transition-colors"
          title="Logout"
        >
          <LogOut className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
