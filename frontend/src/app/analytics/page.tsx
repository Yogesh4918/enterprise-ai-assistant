"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  BarChart3,
  MessageSquare,
  FileText,
  TrendingUp,
  Activity,
  Zap,
  ShieldCheck,
} from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import api from "@/lib/api";

interface UsageStats {
  total_conversations: number;
  total_messages: number;
  total_documents: number;
  indexed_documents: number;
  recent_messages_7d: number;
  average_confidence_score: number | null;
}

interface ActivityPoint {
  date: string;
  count: number;
}

interface DocTypeStat {
  file_type: string;
  count: number;
  total_size: number;
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [activity, setActivity] = useState<ActivityPoint[]>([]);
  const [docStats, setDocStats] = useState<DocTypeStat[]>([]);
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
      loadData();
    }
  }, [isAuthenticated]);

  const loadData = async () => {
    try {
      const [usageData, activityData, docData] = await Promise.allSettled([
        api.getUsageStats(),
        api.getConversationActivity(),
        api.getDocumentStats(),
      ]);

      if (usageData.status === "fulfilled") setStats(usageData.value);
      if (activityData.status === "fulfilled") setActivity(activityData.value.activity);
      if (docData.status === "fulfilled") setDocStats(docData.value.by_type);
    } catch {
      // Silent fail
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading || !isAuthenticated) return null;

  const statCards = [
    {
      label: "Total Conversations",
      value: stats?.total_conversations ?? 0,
      icon: MessageSquare,
      color: "text-brand-purple",
      bgColor: "bg-brand-purple/10",
    },
    {
      label: "Total Messages",
      value: stats?.total_messages ?? 0,
      icon: Zap,
      color: "text-brand-blue",
      bgColor: "bg-brand-blue/10",
    },
    {
      label: "Documents Indexed",
      value: stats?.indexed_documents ?? 0,
      icon: FileText,
      color: "text-brand-green",
      bgColor: "bg-brand-green/10",
    },
    {
      label: "Messages (7 days)",
      value: stats?.recent_messages_7d ?? 0,
      icon: TrendingUp,
      color: "text-brand-orange",
      bgColor: "bg-brand-orange/10",
    },
  ];

  // Calculate max for activity chart
  const maxActivity = Math.max(...activity.map((a) => a.count), 1);

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link href="/" className="p-2 rounded-lg glass hover:bg-white/5 transition-colors">
            <ArrowLeft className="w-5 h-5 text-muted-foreground" />
          </Link>
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-brand-purple" />
              Analytics
            </h1>
            <p className="text-sm text-muted-foreground">Usage statistics and insights</p>
          </div>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="skeleton h-28 rounded-xl" />
            ))}
          </div>
        ) : (
          <>
            {/* Stat Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              {statCards.map((card, i) => (
                <div
                  key={i}
                  className="glass-card p-5 animate-fade-in"
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  <div className={`w-10 h-10 rounded-xl ${card.bgColor} flex items-center justify-center mb-3`}>
                    <card.icon className={`w-5 h-5 ${card.color}`} />
                  </div>
                  <p className="text-2xl font-bold">{card.value.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{card.label}</p>
                </div>
              ))}
            </div>

            {/* Confidence Score */}
            {stats?.average_confidence_score != null && (
              <div className="glass-card p-5 mb-8 animate-fade-in" style={{ animationDelay: "320ms" }}>
                <div className="flex items-center gap-3 mb-3">
                  <ShieldCheck className="w-5 h-5 text-brand-green" />
                  <h2 className="text-sm font-medium">Average Confidence Score</h2>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-3xl font-bold text-brand-green">
                    {Math.round(stats.average_confidence_score * 100)}%
                  </span>
                  <div className="flex-1 h-3 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-brand-green to-brand-blue transition-all duration-1000 ease-out"
                      style={{ width: `${stats.average_confidence_score * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Activity Chart */}
            {activity.length > 0 && (
              <div className="glass-card p-5 mb-8 animate-fade-in" style={{ animationDelay: "400ms" }}>
                <div className="flex items-center gap-3 mb-4">
                  <Activity className="w-5 h-5 text-brand-purple" />
                  <h2 className="text-sm font-medium">Message Activity (30 days)</h2>
                </div>
                <div className="flex items-end gap-1 h-32">
                  {activity.map((point, i) => (
                    <div
                      key={i}
                      className="flex-1 group relative"
                      title={`${point.date}: ${point.count} messages`}
                    >
                      <div
                        className="w-full rounded-t-sm bg-gradient-to-t from-brand-purple/60 to-brand-purple transition-all duration-300 hover:from-brand-purple/80 hover:to-brand-purple"
                        style={{
                          height: `${Math.max(4, (point.count / maxActivity) * 100)}%`,
                        }}
                      />
                      <div className="opacity-0 group-hover:opacity-100 absolute -top-8 left-1/2 -translate-x-1/2 bg-foreground text-background text-[10px] px-2 py-0.5 rounded whitespace-nowrap transition-opacity">
                        {point.count}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex justify-between mt-2 text-[10px] text-muted-foreground/50">
                  <span>{activity[0]?.date}</span>
                  <span>{activity[activity.length - 1]?.date}</span>
                </div>
              </div>
            )}

            {/* Document Stats */}
            {docStats.length > 0 && (
              <div className="glass-card p-5 animate-fade-in" style={{ animationDelay: "480ms" }}>
                <div className="flex items-center gap-3 mb-4">
                  <FileText className="w-5 h-5 text-brand-blue" />
                  <h2 className="text-sm font-medium">Documents by Type</h2>
                </div>
                <div className="space-y-3">
                  {docStats.map((stat, i) => {
                    const totalDocs = docStats.reduce((a, b) => a + b.count, 0);
                    const pct = totalDocs > 0 ? (stat.count / totalDocs) * 100 : 0;
                    return (
                      <div key={i}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="font-medium">{stat.file_type.toUpperCase()}</span>
                          <span className="text-muted-foreground">
                            {stat.count} files · {(stat.total_size / 1024 / 1024).toFixed(1)} MB
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-brand-blue to-brand-purple transition-all duration-500"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
