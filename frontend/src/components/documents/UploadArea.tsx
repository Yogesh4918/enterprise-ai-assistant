"use client";

import React, { useCallback, useState } from "react";
import { Upload, FileText, X, Check, Loader2, AlertCircle } from "lucide-react";
import api from "@/lib/api";
import type { Document } from "@/types";

interface UploadAreaProps {
  onUploadComplete?: (doc: Document) => void;
}

export function UploadArea({ onUploadComplete }: UploadAreaProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploads, setUploads] = useState<{ file: File; status: "uploading" | "done" | "error"; progress: number }[]>([]);

  const handleFiles = useCallback(async (files: FileList | File[]) => {
    const fileArray = Array.from(files);

    for (const file of fileArray) {
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (!["pdf", "docx", "txt"].includes(ext || "")) continue;

      const idx = uploads.length;
      setUploads((prev) => [...prev, { file, status: "uploading", progress: 0 }]);

      try {
        const doc = await api.uploadDocument(file);
        setUploads((prev) => prev.map((u, i) => i === idx ? { ...u, status: "done", progress: 100 } : u));
        onUploadComplete?.(doc);
      } catch {
        setUploads((prev) => prev.map((u, i) => i === idx ? { ...u, status: "error" } : u));
      }
    }
  }, [uploads.length, onUploadComplete]);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
  };

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => {
          const input = document.createElement("input");
          input.type = "file";
          input.accept = ".pdf,.docx,.txt";
          input.multiple = true;
          input.onchange = (e) => {
            const files = (e.target as HTMLInputElement).files;
            if (files) handleFiles(files);
          };
          input.click();
        }}
        className={`
          border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-200
          ${isDragging
            ? "border-brand-purple bg-brand-purple/5 scale-[1.02]"
            : "border-white/10 hover:border-white/20 hover:bg-white/2"
          }
        `}
      >
        <Upload className={`w-10 h-10 mx-auto mb-3 ${isDragging ? "text-brand-purple" : "text-muted-foreground"}`} />
        <p className="text-sm font-medium mb-1">Drop files here or click to upload</p>
        <p className="text-xs text-muted-foreground">Supports PDF, DOCX, TXT — Max 50 MB</p>
      </div>

      {/* Upload progress */}
      {uploads.length > 0 && (
        <div className="space-y-2">
          {uploads.map((upload, i) => (
            <div key={i} className="glass-card flex items-center gap-3 p-3 animate-fade-in">
              <FileText className="w-5 h-5 text-brand-purple flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm truncate">{upload.file.name}</p>
                <p className="text-xs text-muted-foreground">
                  {(upload.file.size / 1024 / 1024).toFixed(1)} MB
                </p>
              </div>
              {upload.status === "uploading" && <Loader2 className="w-4 h-4 text-brand-purple animate-spin" />}
              {upload.status === "done" && <Check className="w-4 h-4 text-green-400" />}
              {upload.status === "error" && <AlertCircle className="w-4 h-4 text-red-400" />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
