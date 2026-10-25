"use client";

import React from "react";
import { OpenWhenLetter } from "@/lib/types";

interface LettersModalProps {
  isOpen: boolean;
  onClose: () => void;
  letters: OpenWhenLetter[];
  onSelectLetter: (letter: OpenWhenLetter) => void;
  onOpenWriteModal: () => void;
}

export function LettersModal({
  isOpen,
  onClose,
  letters,
  onSelectLetter,
  onOpenWriteModal,
}: LettersModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="w-full sm:max-w-lg bg-[var(--bg-card)] border border-[var(--border)] rounded-t-3xl sm:rounded-3xl overflow-hidden shadow-2xl animate-in fade-in slide-in-from-bottom-6 duration-200 flex flex-col max-h-[85vh]">
        <div className="p-5 bg-[var(--mine-bg)] text-white text-center shrink-0">
          <div className="text-3xl mb-1">💌</div>
          <h2 className="text-lg font-extrabold">Open-When Letters</h2>
          <p className="text-xs opacity-90">Digital sealed envelopes for when you need each other</p>
        </div>

        <div className="p-4 flex-1 overflow-y-auto flex flex-col gap-3.5">
          <div className="flex items-center justify-between">
            <span className="text-xs text-[var(--text-sub)] font-semibold">Sealed with wax & love</span>
            <button
              onClick={onOpenWriteModal}
              className="px-3 py-1.5 rounded-xl bg-[var(--mine-bg)] text-white text-xs font-bold active:scale-95 transition-transform shadow-xs"
            >
              + Write a Letter ✍️
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {letters.length === 0 ? (
              <div className="col-span-full text-center py-8 text-xs text-[var(--text-sub)]">
                No sealed letters yet! Be the first to surprise your partner by tapping &ldquo;+ Write a Letter&rdquo; 💕
              </div>
            ) : (
              letters.map((letDoc) => {
                const isSealed = letDoc.is_sealed !== false;
                return (
                  <div
                    key={letDoc.id}
                    onClick={() => onSelectLetter(letDoc)}
                    className={`p-3.5 rounded-2xl border text-center flex flex-col items-center justify-center cursor-pointer active:scale-98 transition-all ${
                      isSealed
                        ? "bg-gradient-to-b from-[var(--accent-dim)] to-transparent border-[var(--accent)] border-dashed shadow-sm"
                        : "bg-[var(--bg-root)] border-[var(--border)] opacity-85"
                    }`}
                  >
                    <div className={`text-3xl mb-1.5 ${isSealed ? "pulse-wax" : ""}`}>
                      {isSealed ? "💌" : "📜"}
                    </div>
                    <div className="text-sm font-extrabold text-white leading-tight">{letDoc.title}</div>
                    <div className="text-[11px] text-[var(--text-sub)] mt-1 truncate max-w-full">
                      {isSealed ? letDoc.open_hint || "Sealed with love 🔒" : "Opened • Read now ✨"}
                    </div>
                    <div className="text-[10px] text-white/50 mt-1.5">From: {letDoc.sender}</div>
                  </div>
                );
              })
            )}
          </div>
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
