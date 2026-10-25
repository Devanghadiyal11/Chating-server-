"use client";

import React, { useState } from "react";
import { MemoryItem } from "@/lib/types";

interface MemoriesModalProps {
  isOpen: boolean;
  onClose: () => void;
  memories: MemoryItem[];
  onOpenPhoto: (src: string, sender: string, time: string) => void;
}

export function MemoriesModal({
  isOpen,
  onClose,
  memories,
  onOpenPhoto,
}: MemoriesModalProps) {
  const [filter, setFilter] = useState<"all" | "photo" | "audio">("all");
  const [playingId, setPlayingId] = useState<string | null>(null);

  if (!isOpen) return null;

  const filtered = memories.filter((m) => {
    if (filter === "photo") return m.type === "photo";
    if (filter === "audio") return m.type === "audio";
    return true;
  });

  const formatTime = (ms: number) => {
    const d = new Date(ms);
    return `${d.toLocaleDateString([], { month: "short", day: "numeric" })} at ${d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true })}`;
  };

  const playVoiceNote = (id: string, src: string) => {
    const audio = new Audio(src);
    audio.onended = () => setPlayingId(null);
    audio.play().catch(() => {});
    setPlayingId(id);
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="w-full sm:max-w-lg bg-[var(--bg-card)] border border-[var(--border)] rounded-t-3xl sm:rounded-3xl overflow-hidden shadow-2xl animate-in fade-in slide-in-from-bottom-6 duration-200 flex flex-col max-h-[85vh]">
        <div className="p-5 bg-[var(--mine-bg)] text-white text-center shrink-0">
          <div className="text-3xl mb-1">📸</div>
          <h2 className="text-lg font-extrabold">Shared Memory Gallery</h2>
          <p className="text-xs opacity-90">All your live photos & voice notes saved forever</p>
        </div>

        <div className="p-4 flex-1 overflow-y-auto flex flex-col gap-3.5">
          {/* Tabs */}
          <div className="flex gap-2">
            {[
              { id: "all", label: "All Moments" },
              { id: "photo", label: "Live Photos 📸" },
              { id: "audio", label: "Voice Notes 🎙️" },
            ].map((t) => (
              <button
                key={t.id}
                onClick={() => setFilter(t.id as "all" | "photo" | "audio")}
                className={`flex-1 py-1.5 rounded-xl text-xs font-bold transition-all ${
                  filter === t.id
                    ? "bg-[var(--mine-bg)] text-white shadow-xs"
                    : "bg-[var(--bg-root)] border border-[var(--border)] text-[var(--text-sub)]"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Grid or List */}
          {filtered.length === 0 ? (
            <div className="text-center py-10 text-xs text-[var(--text-sub)]">
              No captured moments yet. Send live camera photos and voice notes to build your memory book! 📸
            </div>
          ) : filter === "photo" || filter === "all" ? (
            <div className="grid grid-cols-2 gap-2.5">
              {filtered.map((m) => {
                if (m.type === "photo") {
                  return (
                    <div
                      key={m.id}
                      onClick={() => onOpenPhoto(m.src, m.sender, formatTime(m.time_ms))}
                      className="relative aspect-4/3 rounded-2xl overflow-hidden border border-[var(--border)] bg-[var(--bg-root)] cursor-pointer group shadow-xs"
                    >
                      <img src={m.src} alt="Memory" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                      <div className="absolute inset-x-1.5 bottom-1.5 bg-black/70 backdrop-blur-xs p-1.5 rounded-lg flex items-center justify-between text-[10px] text-white">
                        <span className="font-bold truncate">{m.sender}</span>
                        <span className="opacity-80 shrink-0">{new Date(m.time_ms).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</span>
                      </div>
                      <div className="photo-shield" />
                    </div>
                  );
                } else {
                  return (
                    <div
                      key={m.id}
                      className="col-span-2 p-3 rounded-2xl bg-[var(--bg-root)] border border-[var(--border)] flex items-center gap-3"
                    >
                      <button
                        onClick={() => playVoiceNote(m.id, m.src)}
                        className="w-10 h-10 rounded-full bg-[var(--accent-dim)] border border-[var(--accent)] text-white text-base flex items-center justify-center shrink-0"
                      >
                        {playingId === m.id ? "⏸" : "🎙️"}
                      </button>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-bold text-white">Voice Note from {m.sender}</div>
                        <div className="text-[10px] text-[var(--text-sub)] mt-0.5">{formatTime(m.time_ms)}</div>
                      </div>
                    </div>
                  );
                }
              })}
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {filtered.map((m) => (
                <div
                  key={m.id}
                  className="p-3 rounded-2xl bg-[var(--bg-root)] border border-[var(--border)] flex items-center gap-3"
                >
                  <button
                    onClick={() => playVoiceNote(m.id, m.src)}
                    className="w-10 h-10 rounded-full bg-[var(--accent-dim)] border border-[var(--accent)] text-white text-base flex items-center justify-center shrink-0"
                  >
                    {playingId === m.id ? "⏸" : "🎙️"}
                  </button>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-bold text-white">Voice Note from {m.sender}</div>
                    <div className="text-[10px] text-[var(--text-sub)] mt-0.5">{formatTime(m.time_ms)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="p-3 border-t border-[var(--border)] bg-[var(--bg-card)] shrink-0">
          <button
            onClick={onClose}
            className="w-full py-2.5 rounded-xl bg-[var(--bg-root)] border border-[var(--border)] text-xs font-bold text-white"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
