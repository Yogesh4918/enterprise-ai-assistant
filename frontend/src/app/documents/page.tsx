"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, FileText } from "lucide-react";
import Link from "next/link";
import { useAuthStore } from "@/stores/authStore";
import { UploadArea } from "@/components/documents/UploadArea";
import { DocumentList } from "@/components/documents/DocumentList";
import api from "@/lib/api";
import type { Document } from "@/types";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { isAuthenticated, isLoading: authLoading, loadUser } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadDocuments();
    }
  }, [isAuthenticated]);

  const loadDocuments = async () => {
    try {
      const docs = await api.getDocuments();
      setDocuments(docs);
    } catch {
      // Silent fail
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch {
      // Silent fail
    }
  };

  const handleUploadComplete = (doc: Document) => {
    setDocuments((prev) => [doc, ...prev]);
    // Poll for status updates
    const pollInterval = setInterval(async () => {
      try {
        const updated = await api.getDocumentStatus(doc.id);
        setDocuments((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
        if (updated.status === "indexed" || updated.status === "failed") {
          clearInterval(pollInterval);
        }
      } catch {
        clearInterval(pollInterval);
      }
    }, 3000);
  };

  if (authLoading || !isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link
            href="/"
            className="p-2 rounded-lg glass hover:bg-white/5 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-muted-foreground" />
          </Link>
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <FileText className="w-5 h-5 text-brand-purple" />
              Documents
            </h1>
            <p className="text-sm text-muted-foreground">
              Upload and manage your knowledge base
            </p>
          </div>
        </div>

        {/* Upload Area */}
        <div className="mb-8 animate-fade-in">
          <UploadArea onUploadComplete={handleUploadComplete} />
        </div>

        {/* Document List */}
        <div className="animate-fade-in" style={{ animationDelay: "100ms" }}>
          <h2 className="text-sm font-medium text-muted-foreground mb-4">
            Uploaded Documents ({documents.length})
          </h2>
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="skeleton h-32 rounded-xl" />
              ))}
            </div>
          ) : (
            <DocumentList documents={documents} onDelete={handleDelete} />
          )}
        </div>
      </div>
    </div>
  );
}
