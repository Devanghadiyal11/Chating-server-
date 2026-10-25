"use client";

import React, { useState } from "react";

interface WriteLetterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmitLetter: (title: string, content: string, hint: string) => void;
}

const TOPICS = [
  "Open when you miss me 💕",
  "Open on your birthday 🎂",
  "Open when you can't sleep 🌙",
  "Open when we have our first fight 🕊️",
  "Open when you need a tight hug 🤗",
];

export function WriteLetterModal({ isOpen, onClose, onSubmitLetter }: WriteLetterModalProps) {
  const [title, setTitle] = useState("");
  const [hint, setHint] = useState("");
  const [content, setContent] = useState("");

  if (!isOpen) return null;

  const handleSubmit = () => {
    if (!title.trim() || !content.trim()) {
      return alert("Please enter both title and your letter message!");
    }
    onSubmitLetter(title.trim(), content.trim(), hint.trim());
    setTitle("");
    setHint("");
    setContent("");
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="w-full sm:max-w-md bg-[var(--bg-card)] border border-[var(--border)] rounded-t-3xl sm:rounded-3xl overflow-hidden shadow-2xl animate-in fade-in slide-in-from-bottom-6 duration-200">
        <div className="p-5 bg-[var(--mine-bg)] text-white text-center">
          <div className="text-3xl mb-1">✍️</div>
          <h2 className="text-lg font-extrabold">Write an Open-When Letter</h2>
          <p className="text-xs opacity-90">Seal a romantic surprise for your partner</p>
        </div>

        <div className="p-4 flex flex-col gap-3 max-h-[75vh] overflow-y-auto">
          {/* Quick topics */}
          <div>
            <label className="text-xs font-bold text-[var(--text-sub)]">Quick Topics</label>
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {TOPICS.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTitle(t)}
                  className="px-2.5 py-1 rounded-full bg-[var(--bg-root)] border border-[var(--border)] text-[11px] font-semibold text-[var(--text-main)] active:scale-95 hover:border-[var(--accent)]"
                >
                  {t.split(" ")[2] || t.slice(0, 12)}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-[var(--text-sub)]">Letter Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Open when you miss me 💕"
              className="w-full mt-1 bg-[var(--bg-root)] border border-[var(--border)] rounded-xl px-3.5 py-2 text-sm text-[var(--text-main)] focus:outline-none focus:border-[var(--accent)]"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-[var(--text-sub)]">When to Open (Hint)</label>
            <input
              type="text"
              value={hint}
              onChange={(e) => setHint(e.target.value)}
              placeholder="e.g. For when we are miles apart..."
              className="w-full mt-1 bg-[var(--bg-root)] border border-[var(--border)] rounded-xl px-3.5 py-2 text-sm text-[var(--text-main)] focus:outline-none focus:border-[var(--accent)]"
            />
          </div>

          <div>
            <label className="text-xs font-bold text-[var(--text-sub)]">Your Heartfelt Words</label>
            <textarea
              rows={5}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write your deepest feelings here..."
              className="w-full mt-1 bg-[var(--bg-root)] border border-[var(--border)] rounded-xl px-3.5 py-2 text-sm text-[var(--text-main)] focus:outline-none focus:border-[var(--accent)] resize-none"
            />
          </div>

          <button
            onClick={handleSubmit}
            className="w-full py-3 rounded-xl bg-[var(--mine-bg)] text-white text-xs font-bold shadow-md active:scale-98 transition-transform"
          >
            Seal With Love & Wax 💌
          </button>
          <button
            onClick={onClose}
            className="w-full py-2 rounded-xl bg-[var(--bg-root)] border border-[var(--border)] text-xs text-white"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
