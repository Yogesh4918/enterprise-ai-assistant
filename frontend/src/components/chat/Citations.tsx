"use client";

import React, { useState } from "react";
import type { Citation } from "@/types";
import { FileText, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { SourcePreview } from "./SourcePreview";

interface CitationsProps {
  citations: Citation[];
}

export function Citations({ citations }: CitationsProps) {
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);

  if (!citations || citations.length === 0) return null;

  return (
    <>
      <div className="flex flex-wrap gap-2 mt-2 animate-fade-in">
        {citations.map((citation, idx) => (
          <button
            key={idx}
            onClick={() => setSelectedCitation(citation)}
            className="glass-card flex items-center gap-2 px-3 py-1.5 text-xs hover:border-brand-purple/40 transition-all duration-200 cursor-pointer group"
          >
            <FileText className="w-3 h-3 text-brand-purple" />
            <span className="text-muted-foreground group-hover:text-foreground transition-colors">
              {citation.source}
            </span>
            {citation.page != null && (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                p.{citation.page}
              </Badge>
            )}
            <div
              className="w-1.5 h-1.5 rounded-full"
              style={{
                backgroundColor: citation.relevance_score > 0.8 ? "#10b981" : citation.relevance_score > 0.5 ? "#f59e0b" : "#ef4444",
              }}
            />
          </button>
        ))}
      </div>

      {selectedCitation && (
        <SourcePreview
          citation={selectedCitation}
          onClose={() => setSelectedCitation(null)}
        />
      )}
    </>
  );
}
