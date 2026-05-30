"use client";

import React, { useState, useRef, useEffect } from "react";
import { Mic, Square, Loader2 } from "lucide-react";
import api from "@/lib/api";

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  onCancel: () => void;
}

export function VoiceInput({ onTranscript, onCancel }: VoiceInputProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [duration, setDuration] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    startRecording();
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      mediaRecorderRef.current?.stop();
    };
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        if (timerRef.current) clearInterval(timerRef.current);

        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size > 0) {
          setIsTranscribing(true);
          try {
            const result = await api.transcribeAudio(blob);
            if (result.text) onTranscript(result.text);
            else onCancel();
          } catch {
            onCancel();
          }
        } else {
          onCancel();
        }
      };

      mediaRecorder.start(250);
      setIsRecording(true);
      timerRef.current = setInterval(() => setDuration((d) => d + 1), 1000);
    } catch {
      onCancel();
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  const formatDuration = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;

  if (isTranscribing) {
    return (
      <div className="flex items-center gap-2 px-3">
        <Loader2 className="w-4 h-4 text-brand-purple animate-spin" />
        <span className="text-xs text-muted-foreground">Transcribing...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 px-2">
      {/* Waveform */}
      <div className="voice-wave">
        {[...Array(5)].map((_, i) => (
          <span key={i} style={{ height: `${8 + Math.random() * 16}px` }} />
        ))}
      </div>

      <span className="text-xs text-red-400 font-mono min-w-[36px]">
        {formatDuration(duration)}
      </span>

      <button
        onClick={stopRecording}
        className="p-1.5 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors recording-pulse"
        title="Stop recording"
      >
        <Square className="w-3.5 h-3.5" />
      </button>

      <button
        onClick={() => { mediaRecorderRef.current?.stop(); onCancel(); }}
        className="text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        Cancel
      </button>
    </div>
  );
}
