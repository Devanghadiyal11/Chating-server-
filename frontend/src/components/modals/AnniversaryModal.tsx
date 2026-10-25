"use client";

import React, { useState } from "react";

interface AnniversaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentDate: string;
  currentName: string;
  onSave: (date: string, name: string) => void;
}

export function AnniversaryModal({
  isOpen,
  onClose,
  currentDate,
  currentName,
  onSave,
}: AnniversaryModalProps) {
  const [date, setDate] = useState(currentDate || "2024-02-14");
  const [name, setName] = useState(currentName || "Our Sweet Space 💕");

  if (!isOpen) return null;

  const handleSave = () => {
    if (!date) return alert("Please select a date!");
    onSave(date, name.trim() || "Our Sweet Space 💕");
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="w-full sm:max-w-md bg-[var(--bg-card)] border border-[var(--border)] rounded-t-3xl sm:rounded-3xl overflow-hidden shadow-2xl animate-in fade-in slide-in-from-bottom-6 duration-200">
        <div className="p-5 bg-[var(--mine-bg)] text-white text-center">
          <div className="text-3xl mb-1">💍</div>
          <h2 className="text-lg font-extrabold">When Did Your Love Begin?</h2>
          <p className="text-xs opacity-90">Set your special anniversary date & name</p>
        </div>

        <div className="p-4 flex flex-col gap-3.5">
          <div>
            <label className="text-xs font-bold text-[var(--text-sub)]">Anniversary Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full mt-1.5 bg-[var(--bg-root)] border border-[var(--border)] rounded-xl px-3.5 py-2.5 text-sm text-[var(--text-main)] focus:outline-none focus:border-[var(--accent)]"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-[var(--text-sub)]">Couple Space Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Dev & Babe 💕"
              className="w-full mt-1.5 bg-[var(--bg-root)] border border-[var(--border)] rounded-xl px-3.5 py-2.5 text-sm text-[var(--text-main)] focus:outline-none focus:border-[var(--accent)]"
            />
          </div>

          <button
            onClick={handleSave}
            className="w-full py-3 rounded-xl bg-[var(--mine-bg)] text-white text-xs font-bold shadow-md active:scale-98 transition-transform"
          >
            Save & Celebrate 💕
          </button>
          <button
            onClick={onClose}
            className="w-full py-2.5 rounded-xl bg-[var(--bg-root)] border border-[var(--border)] text-xs text-white"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
