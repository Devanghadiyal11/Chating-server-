"use client";

import React, { useState } from "react";
import { CheckInDoc } from "@/lib/types";

interface CheckInModalProps {
  isOpen: boolean;
  onClose: () => void;
  partnerCheckin: CheckInDoc | null;
  onSubmitCheckin: (mood: string, note: string) => void;
}

const MOODS = [
  { emoji: "🥰", label: "In Love" },
  { emoji: "😊", label: "Happy" },
  { emoji: "🥺", label: "Miss You" },
  { emoji: "😴", label: "Tired" },
  { emoji: "☕", label: "Relaxed" },
  { emoji: "😤", label: "Stressed" },
  { emoji: "🤒", label: "Unwell" },
  { emoji: "✨", label: "Excited" },
];

export function CheckInModal({
  isOpen,
  onClose,
  partnerCheckin,
  onSubmitCheckin,
}: CheckInModalProps) {
  const [selectedMood, setSelectedMood] = useState("🥰");
  const [note, setNote] = useState("");

  if (!isOpen) return null;

  const handleSave = () => {
    onSubmitCheckin(selectedMood, note.trim());
    onClose();
  };

  const formatTime = (ms: number) => {
    return new Date(ms).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true });
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="w-full sm:max-w-md bg-[var(--bg-card)] border border-[var(--border)] rounded-t-3xl sm:rounded-3xl overflow-hidden shadow-2xl animate-in fade-in slide-in-from-bottom-6 duration-200">
        <div className="p-5 bg-[var(--mine-bg)] text-white text-center">
          <div className="text-3xl mb-1">🥰</div>
          <h2 className="text-lg font-extrabold">Daily Check-In</h2>
          <p className="text-xs opacity-90">How are you feeling right now?</p>
        </div>

        <div className="p-4 flex flex-col gap-3.5 max-h-[75vh] overflow-y-auto">
          {/* Partner's Today Mood Card */}
          <div className="p-3 rounded-2xl bg-[var(--bg-root)] border border-dashed border-[var(--accent)] flex items-center gap-3">
            <div className="text-3xl">{partnerCheckin?.mood || "💭"}</div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-bold text-[var(--accent)]">
                {partnerCheckin ? `${partnerCheckin.username}'s Mood Today 💕` : "Her Mood Today 💕"}
              </div>
              <div className="text-sm font-bold text-white truncate">
                {partnerCheckin?.note ? `"${partnerCheckin.note}"` : (partnerCheckin ? "Feeling happy 💕" : "Waiting for today's check-in 💕")}
              </div>
              <div className="text-[10px] text-[var(--text-sub)] mt-0.5">
                {partnerCheckin ? `Updated at ${formatTime(partnerCheckin.updated_at)}` : "Tap below to update your mood first!"}
              </div>
            </div>
          </div>

          {/* Mood Selector Grid */}
          <div>
            <label className="text-xs font-bold text-[var(--text-sub)]">Select Your Mood</label>
            <div className="grid grid-cols-4 gap-2 mt-1.5">
              {MOODS.map((m) => {
                const isSelected = selectedMood === m.emoji;
                return (
                  <button
                    key={m.label}
                    onClick={() => setSelectedMood(m.emoji)}
                    className={`p-2.5 rounded-xl border flex flex-col items-center gap-1 active:scale-95 transition-all ${
                      isSelected
                        ? "bg-[var(--accent-dim)] border-[var(--accent)] shadow-md"
                        : "bg-[var(--bg-root)] border-[var(--border)] opacity-85"
                    }`}
                  >
                    <span className="text-2xl">{m.emoji}</span>
                    <span className="text-[10px] font-bold text-[var(--text-main)]">{m.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Sweet Note Input */}
          <div>
            <label className="text-xs font-bold text-[var(--text-sub)]">Add a Sweet Note (Optional)</label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Can't stop smiling thinking of you..."
              className="w-full mt-1.5 bg-[var(--bg-root)] border border-[var(--border)] rounded-xl px-3.5 py-2.5 text-base sm:text-sm text-[var(--text-main)] placeholder-[var(--text-sub)]/60 focus:outline-none focus:border-[var(--accent)]"
            />
          </div>

          <button
            onClick={handleSave}
            className="w-full py-3 rounded-xl bg-[var(--mine-bg)] text-white text-sm font-extrabold shadow-md active:scale-98 transition-transform"
          >
            Update My Mood 💕
          </button>
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
