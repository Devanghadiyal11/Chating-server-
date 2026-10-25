"use client";

import React from "react";
import { ThemeType } from "@/lib/types";

interface QuickBarProps {
  currentTheme: ThemeType;
  onOpenThemeModal: () => void;
  onOpenCheckIn: () => void;
  onOpenLetters: () => void;
  onOpenTimeline: () => void;
  onOpenMemories: () => void;
}

const THEME_ICONS: Record<ThemeType, string> = {
  rose: "🌸",
  lavender: "💜",
  sunset: "🌅",
  noir: "🌙",
  cream: "☁️",
};

export function QuickBar({
  currentTheme,
  onOpenThemeModal,
  onOpenCheckIn,
  onOpenLetters,
  onOpenTimeline,
  onOpenMemories,
}: QuickBarProps) {
  return (
    <div className="flex items-center gap-1.5 sm:gap-2 px-3 py-1.5 bg-[var(--bg-card)] border-b border-[var(--border)] overflow-x-auto no-scrollbar shrink-0 z-9">
      <button
        onClick={onOpenThemeModal}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--accent-dim)] border border-[var(--accent)] text-white text-xs font-bold shrink-0 active:scale-95 transition-transform"
      >
        <span className="text-sm">{THEME_ICONS[currentTheme] || "🎨"}</span>
        <span>Theme</span>
      </button>

      <button
        onClick={onOpenCheckIn}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--bg-root)] border border-[var(--border)] text-[var(--text-main)] text-xs font-bold shrink-0 active:scale-95 transition-transform"
      >
        <span className="text-sm">🥰</span>
        <span>Daily Check-In</span>
      </button>

      <button
        onClick={onOpenLetters}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--bg-root)] border border-[var(--border)] text-[var(--text-main)] text-xs font-bold shrink-0 active:scale-95 transition-transform"
      >
        <span className="text-sm">💌</span>
        <span>Letters</span>
      </button>

      <button
        onClick={onOpenTimeline}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--bg-root)] border border-[var(--border)] text-[var(--text-main)] text-xs font-bold shrink-0 active:scale-95 transition-transform"
      >
        <span className="text-sm">⏳</span>
        <span>Timeline</span>
      </button>

      <button
        onClick={onOpenMemories}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--bg-root)] border border-[var(--border)] text-[var(--text-main)] text-xs font-bold shrink-0 active:scale-95 transition-transform"
      >
        <span className="text-sm">📸</span>
        <span>Memories</span>
      </button>
    </div>
  );
}
