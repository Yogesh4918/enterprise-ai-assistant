"use client";

import React from "react";
import { FileText, Trash2, FileType, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { Document } from "@/types";
import { formatDate } from "@/lib/utils";

interface DocumentListProps {
  documents: Document[];
  onDelete: (id: string) => void;
}

const FILE_ICONS: Record<string, string> = {
  pdf: "📄",
  docx: "📝",
  txt: "📃",
};

const STATUS_COLORS: Record<string, string> = {
  uploading: "bg-blue-400/20 text-blue-400",
  processing: "bg-yellow-400/20 text-yellow-400",
  indexed: "bg-green-400/20 text-green-400",
  failed: "bg-red-400/20 text-red-400",
};

export function DocumentList({ documents, onDelete }: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">No documents uploaded yet</p>
        <p className="text-xs text-muted-foreground/60 mt-1">Upload PDF, DOCX, or TXT files to get started</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {documents.map((doc) => (
        <div key={doc.id} className="glass-card p-4 group animate-fade-in hover:border-white/10 transition-all">
          <div className="flex items-start justify-between mb-3">
            <span className="text-2xl">{FILE_ICONS[doc.file_type] || "📄"}</span>
            <Badge className={`text-[10px] ${STATUS_COLORS[doc.status] || ""}`}>
              {doc.status === "processing" && (
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-yellow-400 mr-1 animate-pulse" />
              )}
              {doc.status}
            </Badge>
          </div>

          <h3 className="text-sm font-medium truncate mb-1" title={doc.filename}>
            {doc.filename}
          </h3>

          <div className="flex items-center gap-3 text-[11px] text-muted-foreground mb-3">
            <span className="flex items-center gap-1">
              <FileType className="w-3 h-3" />
              {doc.file_type.toUpperCase()}
            </span>
            <span>{(doc.file_size / 1024 / 1024).toFixed(1)} MB</span>
            {doc.chunk_count > 0 && <span>{doc.chunk_count} chunks</span>}
          </div>

          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1 text-[10px] text-muted-foreground/60">
              <Clock className="w-3 h-3" />
              {formatDate(doc.created_at)}
            </span>
            <button
              onClick={() => onDelete(doc.id)}
              className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-all"
              title="Delete document"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
