"use client";

import React from "react";
import { OpenWhenLetter } from "@/lib/types";

interface LetterViewerModalProps {
  letter: OpenWhenLetter | null;
  onClose: () => void;
}

export function LetterViewerModal({ letter, onClose }: LetterViewerModalProps) {
  if (!letter) return null;

  const formatOpenedDate = (ms?: number | null) => {
    if (!ms) return "Opened with love 💕";
    const d = new Date(ms);
    return `Opened on ${d.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" })} at ${d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true })}`;
  };

  return (
    <div className="fixed inset-0 bg-black/85 backdrop-blur-xs z-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-[var(--bg-card)] border border-[var(--border)] rounded-3xl overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 bg-gradient-to-r from-red-600 to-rose-700 text-white text-center">
          <div className="text-3xl mb-1">📜</div>
          <h2 className="text-base sm:text-lg font-extrabold leading-tight">{letter.title}</h2>
          <p className="text-xs opacity-90 mt-0.5">Written with pure love by {letter.sender} 💕</p>
        </div>

        <div className="p-5 flex flex-col gap-3">
          <div className="p-4 rounded-2xl bg-[var(--bg-root)] border border-[var(--border)] text-sm sm:text-base leading-relaxed text-[var(--text-main)] max-h-[300px] overflow-y-auto whitespace-pre-wrap font-serif">
            {letter.content}
          </div>

          <div className="text-center text-[11px] text-[var(--text-sub)]">
            {formatOpenedDate(letter.opened_at)}
          </div>

          <button
            onClick={onClose}
            className="w-full py-3 rounded-xl bg-[var(--mine-bg)] text-white text-xs font-bold active:scale-98 transition-transform shadow-md"
          >
            Keep In My Heart 💕
          </button>
        </div>
      </div>
    </div>
  );
}
