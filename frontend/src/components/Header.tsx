"use client";

import React from "react";

interface HeaderProps {
  coupleName: string;
  daysTogether: number;
  nudgeCooldown: number;
  soundEnabled: boolean;
  onOpenSidebar: () => void;
  onOpenAnniversary: () => void;
  onOpenThemeModal: () => void;
  onSendNudge: () => void;
  onToggleSound: () => void;
  onToggleStealth: () => void;
}

export function Header({
  coupleName,
  daysTogether,
  nudgeCooldown,
  soundEnabled,
  onOpenSidebar,
  onOpenAnniversary,
  onOpenThemeModal,
  onSendNudge,
  onToggleSound,
  onToggleStealth,
}: HeaderProps) {
  return (
    <header className="px-3 sm:px-4 py-2 border-b border-[var(--border)] bg-[var(--bg-dark)] flex items-center justify-between shrink-0 z-10">
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        <button
          onClick={onOpenSidebar}
          className="lg:hidden w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text-main)] flex items-center justify-center text-lg active:scale-95 transition-transform"
          aria-label="Open menu"
        >
          ☰
        </button>
        <div className="flex flex-col min-w-0">
          <div className="text-sm sm:text-base font-extrabold text-white flex items-center gap-1.5 truncate">
            <span className="truncate">{coupleName}</span>
            <span className="text-xs sm:text-sm">💕</span>
          </div>
          <button
            onClick={onOpenAnniversary}
            className="text-[11px] sm:text-xs text-[var(--accent)] font-bold text-left truncate flex items-center gap-1 hover:underline"
          >
            <span>✨ Together {daysTogether} days 💕</span>
          </button>
        </div>
      </div>

      <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
        {/* Synced Theme Switcher */}
        <button
          onClick={onOpenThemeModal}
          className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] text-sm sm:text-base flex items-center justify-center active:scale-92 transition-transform"
          title="Synced Couple Theme 🎨"
        >
          🎨
        </button>

        {/* Love Nudge / Thinking of You */}
        <button
          onClick={onSendNudge}
          disabled={nudgeCooldown > 0}
          className={`w-9 h-9 sm:w-10 sm:h-10 rounded-xl border flex items-center justify-center text-sm sm:text-base transition-transform active:scale-92 ${
            nudgeCooldown > 0
              ? "bg-[var(--bg-card)] border-[var(--border)] text-[var(--accent)] font-black text-xs cursor-not-allowed opacity-75"
              : "bg-[var(--accent-dim)] border-[var(--accent)] text-[var(--accent)] animate-pulse"
          }`}
          title="Thinking of You! 💖"
        >
          {nudgeCooldown > 0 ? `${nudgeCooldown}s` : "💖"}
        </button>

        {/* Sound Toggle */}
        <button
          onClick={onToggleSound}
          className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] text-sm sm:text-base flex items-center justify-center active:scale-92 transition-transform"
          title={soundEnabled ? "Sound: ON" : "Sound: Muted"}
        >
          {soundEnabled ? "🔔" : "🔕"}
        </button>

        {/* Stealth / Panic Disguise */}
        <button
          onClick={onToggleStealth}
          className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] text-sm sm:text-base flex items-center justify-center active:scale-92 transition-transform"
          title="Disguise Mode (Panic Esc)"
        >
          🕵️
        </button>
      </div>
    </header>
  );
}
