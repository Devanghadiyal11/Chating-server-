"use client";

import React from "react";
import { ThemeType } from "@/lib/types";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  coupleName: string;
  daysTogether: number;
  currentUser: string;
  currentAvatar: string;
  onlineUsers: string[];
  currentTheme: ThemeType;
  disappearingMode: number;
  onSelectTheme: (theme: ThemeType) => void;
  onChangeDisappearing: (seconds: number) => void;
  onOpenAnniversary: () => void;
  onOpenCheckIn: () => void;
  onOpenTimeline: () => void;
  onOpenLetters: () => void;
  onOpenMemories: () => void;
  onClearChat: () => void;
  onLogout: () => void;
}

export function Sidebar({
  isOpen,
  onClose,
  coupleName,
  daysTogether,
  currentUser,
  currentAvatar,
  onlineUsers,
  currentTheme,
  disappearingMode,
  onSelectTheme,
  onChangeDisappearing,
  onOpenAnniversary,
  onOpenCheckIn,
  onOpenTimeline,
  onOpenLetters,
  onOpenMemories,
  onClearChat,
  onLogout,
}: SidebarProps) {
  const copyInviteLink = () => {
    if (typeof window === "undefined") return;
    const link = `${window.location.origin}/?pin=1012`;
    navigator.clipboard.writeText(link).then(() => {
      alert("✨ Copied direct link to clipboard!\nSend this link to your girlfriend so she can join in 1 tap:\n\n" + link);
    }).catch(() => {
      prompt("Copy invite link for your girlfriend:", link);
    });
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/70 backdrop-blur-xs z-40 lg:hidden transition-opacity"
        />
      )}

      {/* Sidebar Drawer */}
      <aside
        className={`fixed lg:static top-0 bottom-0 left-0 w-[290px] bg-[var(--bg-dark)] border-r border-[var(--border)] flex flex-col z-50 transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        {/* Sidebar Header */}
        <div className="p-4 border-b border-[var(--border)] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-[var(--accent-dim)] border border-[var(--accent)] flex items-center justify-center text-xl shadow-sm">
              💖
            </div>
            <div>
              <div className="font-extrabold text-white text-sm truncate max-w-[170px]">
                {coupleName}
              </div>
              <div className="text-[11px] text-[var(--accent)] font-semibold">
                Private Couple Space 💕
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden w-8 h-8 rounded-lg bg-[var(--bg-card)] border border-[var(--border)] text-sm flex items-center justify-center"
          >
            ✕
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-3.5 flex flex-col gap-3">
          {/* Days Together */}
          <div
            onClick={onOpenAnniversary}
            className="p-3.5 rounded-2xl bg-gradient-to-b from-[var(--accent-dim)] to-transparent border border-dashed border-[var(--accent)] text-center cursor-pointer active:scale-98 transition-transform"
          >
            <div className="text-2xl font-black text-[var(--accent)]">{daysTogether}</div>
            <div className="text-[11px] text-[var(--text-sub)] font-semibold mt-0.5">
              Days of Loving You 💕
            </div>
          </div>

          {/* Special Moments Hub */}
          <div className="p-3 rounded-2xl bg-[var(--bg-card)] border border-[var(--border)]">
            <div className="text-[10px] font-extrabold uppercase text-[var(--text-sub)] tracking-wider mb-2">
              Our Special Moments 💕
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => { onOpenCheckIn(); onClose(); }}
                className="p-2 rounded-xl bg-[var(--bg-root)] border border-[var(--border)] flex flex-col items-center gap-1 active:scale-95 transition-transform"
              >
                <span className="text-lg">🥰</span>
                <span className="text-[11px] font-bold text-white">Check-In</span>
              </button>

              <button
                onClick={() => { onOpenTimeline(); onClose(); }}
                className="p-2 rounded-xl bg-[var(--bg-root)] border border-[var(--border)] flex flex-col items-center gap-1 active:scale-95 transition-transform"
              >
                <span className="text-lg">⏳</span>
                <span className="text-[11px] font-bold text-white">Timeline</span>
              </button>

              <button
                onClick={() => { onOpenLetters(); onClose(); }}
                className="p-2 rounded-xl bg-[var(--bg-root)] border border-[var(--border)] flex flex-col items-center gap-1 active:scale-95 transition-transform"
              >
                <span className="text-lg">💌</span>
                <span className="text-[11px] font-bold text-white">Letters</span>
              </button>

              <button
                onClick={() => { onOpenMemories(); onClose(); }}
                className="p-2 rounded-xl bg-[var(--bg-root)] border border-[var(--border)] flex flex-col items-center gap-1 active:scale-95 transition-transform"
              >
                <span className="text-lg">📸</span>
                <span className="text-[11px] font-bold text-white">Memories</span>
              </button>
            </div>
          </div>

          {/* Current Profile */}
          <div className="p-3 rounded-2xl bg-[var(--bg-card)] border border-[var(--border)] flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-full bg-[var(--accent-dim)] border border-[var(--accent)] flex items-center justify-center text-lg">
                {currentAvatar}
              </div>
              <div>
                <div className="text-xs font-bold text-white">{currentUser} (you)</div>
                <div className="text-[10px] text-emerald-400 font-semibold flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  Active
                </div>
              </div>
            </div>
          </div>

          {/* Online Partner Card */}
          <div className="p-3 rounded-2xl bg-[var(--bg-card)] border border-[var(--border)]">
            <div className="flex items-center justify-between text-[10px] font-extrabold uppercase text-[var(--text-sub)] tracking-wider mb-2">
              <span>In Our Space</span>
              <span className="text-[var(--accent)]">{onlineUsers.length} online</span>
            </div>
            <div className="flex flex-col gap-1.5">
              {onlineUsers.length === 0 ? (
                <div className="text-xs text-[var(--text-sub)]">Waiting for your partner...</div>
              ) : (
                onlineUsers.map((u) => {
                  const isMe = u.toLowerCase() === currentUser.toLowerCase();
                  return (
                    <div key={u} className="flex items-center gap-2 text-xs font-semibold">
                      <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                      <span className={isMe ? "text-[var(--accent)] font-bold" : "text-white"}>
                        {u} {isMe ? "(you)" : "💕"}
                      </span>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Color Themes */}
          <div className="p-3 rounded-2xl bg-[var(--bg-card)] border border-[var(--border)]">
            <div className="text-[10px] font-extrabold uppercase text-[var(--text-sub)] tracking-wider mb-2">
              Couple Theme (Synced 💕)
            </div>
            <div className="grid grid-cols-5 gap-1.5">
              {[
                { id: "rose", bg: "#e11d48", label: "🌸" },
                { id: "lavender", bg: "#7c3aed", label: "💜" },
                { id: "sunset", bg: "#ea580c", label: "🌅" },
                { id: "noir", bg: "#ff2e93", label: "🌙" },
                { id: "cream", bg: "#e05d76", label: "☁️" },
              ].map((t) => (
                <button
                  key={t.id}
                  onClick={() => onSelectTheme(t.id as ThemeType)}
                  style={{ background: t.bg }}
                  className={`h-9 rounded-xl flex items-center justify-center text-sm shadow-sm transition-transform active:scale-95 ${
                    currentTheme === t.id ? "ring-2 ring-white scale-105" : "opacity-80"
                  }`}
                  title={t.id}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Disappearing Messages */}
          <div className="p-3 rounded-2xl bg-[var(--bg-card)] border border-[var(--border)]">
            <div className="text-[10px] font-extrabold uppercase text-[var(--text-sub)] tracking-wider mb-1.5">
              Disappearing Messages
            </div>
            <select
              value={disappearingMode}
              onChange={(e) => onChangeDisappearing(parseInt(e.target.value, 10))}
              className="w-full bg-[var(--bg-root)] border border-[var(--border)] rounded-xl px-2.5 py-2 text-xs text-[var(--text-main)] focus:outline-none"
            >
              <option value="0">Off (Keep forever)</option>
              <option value="3600">Disappear after 1 hour</option>
              <option value="86400">Disappear after 24 hours</option>
            </select>
          </div>

          {/* Copy Direct Link */}
          <button
            onClick={copyInviteLink}
            className="w-full py-2.5 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] text-xs font-bold text-white hover:border-[var(--accent)] transition-colors flex items-center justify-center gap-1.5"
          >
            <span>🔗 Copy Link for Her</span>
          </button>
        </div>

        {/* Footer */}
        <div className="p-3.5 border-t border-[var(--border)] flex gap-2">
          <button
            onClick={onClearChat}
            className="flex-1 py-2 rounded-xl bg-red-500/15 border border-red-500/30 text-red-400 text-xs font-bold active:scale-95 transition-transform"
          >
            🗑️ Clear
          </button>
          <button
            onClick={onLogout}
            className="flex-1 py-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] text-white text-xs font-bold active:scale-95 transition-transform"
          >
            🚪 Leave
          </button>
        </div>
      </aside>
    </>
  );
}
