"use client";

import React from "react";
import { ThemeType } from "@/lib/types";

interface ThemeModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTheme: ThemeType;
  onSelectTheme: (theme: ThemeType) => void;
}

const THEMES: { id: ThemeType; name: string; desc: string; gradient: string; border: string }[] = [
  {
    id: "rose",
    name: "🌸 Rose Blossom",
    desc: "Romantic dark rose & glowing pink",
    gradient: "linear-gradient(135deg, #e11d48, #0c0a10)",
    border: "#e11d48",
  },
  {
    id: "lavender",
    name: "💜 Midnight Lavender",
    desc: "Dreamy purple night with soft glow",
    gradient: "linear-gradient(135deg, #7c3aed, #090814)",
    border: "#7c3aed",
  },
  {
    id: "sunset",
    name: "🌅 Sunset Warmth",
    desc: "Golden amber warmth & sweet sunset",
    gradient: "linear-gradient(135deg, #ea580c, #130a0a)",
    border: "#ea580c",
  },
  {
    id: "noir",
    name: "🌙 OLED Noir",
    desc: "Pure ink black with cyber neon pink",
    gradient: "linear-gradient(135deg, #ff2e93, #000000)",
    border: "#ff2e93",
  },
  {
    id: "cream",
    name: "☁️ Cozy Cream",
    desc: "Warm aesthetic daylight & gentle rose",
    gradient: "linear-gradient(135deg, #e05d76, #faf5ef)",
    border: "#e05d76",
  },
];

export function ThemeModal({ isOpen, onClose, currentTheme, onSelectTheme }: ThemeModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="w-full sm:max-w-md bg-[var(--bg-card)] border border-[var(--border)] rounded-t-3xl sm:rounded-3xl overflow-hidden shadow-2xl animate-in fade-in slide-in-from-bottom-6 duration-200">
        <div className="p-5 bg-[var(--mine-bg)] text-white text-center">
          <div className="text-3xl mb-1">🎨</div>
          <h2 className="text-lg font-extrabold">Couple Theme 💕</h2>
          <p className="text-xs opacity-90">Changing theme updates it in real time for BOTH of you!</p>
        </div>

        <div className="p-4 flex flex-col gap-2.5 max-h-[60vh] overflow-y-auto">
          {THEMES.map((t) => {
            const isSelected = currentTheme === t.id;
            return (
              <div
                key={t.id}
                onClick={() => {
                  onSelectTheme(t.id);
                  onClose();
                }}
                className={`flex items-center gap-3 p-3 rounded-2xl bg-[var(--bg-root)] border cursor-pointer active:scale-98 transition-all ${
                  isSelected
                    ? "border-[var(--accent)] bg-[var(--accent-dim)] shadow-md"
                    : "border-[var(--border)] hover:border-[var(--accent)]/50"
                }`}
              >
                <div
                  style={{ background: t.gradient, borderColor: t.border }}
                  className="w-10 h-10 rounded-xl border-2 shrink-0 shadow-sm"
                />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-white">{t.name}</div>
                  <div className="text-xs text-[var(--text-sub)] truncate">{t.desc}</div>
                </div>
                {isSelected && <span className="text-[var(--accent)] font-extrabold text-lg mr-1">✓</span>}
              </div>
            );
          })}

          <button
            onClick={onClose}
            className="w-full py-2.5 mt-2 rounded-xl bg-[var(--bg-root)] border border-[var(--border)] text-xs font-bold text-white"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
