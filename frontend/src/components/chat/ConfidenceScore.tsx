"use client";

import React from "react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ShieldCheck } from "lucide-react";

interface ConfidenceScoreProps {
  score: number;
}

export function ConfidenceScore({ score }: ConfidenceScoreProps) {
  const percentage = Math.round(score * 100);
  const color = score > 0.8 ? "#10b981" : score > 0.5 ? "#f59e0b" : "#ef4444";
  const label = score > 0.8 ? "High confidence" : score > 0.5 ? "Medium confidence" : "Low confidence";

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger>
          <div className="flex items-center gap-1.5 mt-1.5 cursor-help">
            <ShieldCheck className="w-3 h-3" style={{ color }} />
            <div className="w-16 h-1.5 rounded-full bg-white/5 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500 ease-out"
                style={{ width: `${percentage}%`, backgroundColor: color }}
              />
            </div>
            <span className="text-[10px]" style={{ color }}>{percentage}%</span>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p className="text-xs">{label} — Based on retrieval relevance scores</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
