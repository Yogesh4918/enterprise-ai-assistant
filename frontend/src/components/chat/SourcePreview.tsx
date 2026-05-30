"use client";

import React from "react";
import type { Citation } from "@/types";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { FileText, Hash, BarChart3 } from "lucide-react";

interface SourcePreviewProps {
  citation: Citation;
  onClose: () => void;
}

export function SourcePreview({ citation, onClose }: SourcePreviewProps) {
  const relevanceColor = citation.relevance_score > 0.8 ? "text-green-400" : citation.relevance_score > 0.5 ? "text-yellow-400" : "text-red-400";
  const relevanceLabel = citation.relevance_score > 0.8 ? "High" : citation.relevance_score > 0.5 ? "Medium" : "Low";

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="sm:max-w-xl glass border-border/50">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <FileText className="w-5 h-5 text-brand-purple" />
            Source Preview
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Metadata */}
          <div className="flex flex-wrap gap-3 text-sm">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <FileText className="w-3.5 h-3.5" />
              <span className="font-medium text-foreground">{citation.source}</span>
            </div>
            {citation.page != null && (
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Hash className="w-3.5 h-3.5" />
                Page {citation.page}
              </div>
            )}
            <div className="flex items-center gap-1.5">
              <BarChart3 className={`w-3.5 h-3.5 ${relevanceColor}`} />
              <span className={relevanceColor}>
                {relevanceLabel} relevance ({Math.round(citation.relevance_score * 100)}%)
              </span>
            </div>
          </div>

          {/* Content */}
          <div className="glass-card p-4 rounded-xl">
            <p className="text-sm leading-relaxed text-foreground/90 whitespace-pre-wrap">
              {citation.chunk_text}
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
