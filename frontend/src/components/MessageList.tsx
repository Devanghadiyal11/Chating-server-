"use client";

import React, { useRef, useEffect, useState } from "react";
import { ChatMessage, DeliveryStatus } from "@/lib/types";
import { burstHearts } from "@/lib/audio";

interface MessageListProps {
  messages: ChatMessage[];
  currentUser: string;
  onToggleReaction: (msgId: string, emoji: string) => void;
  onDeleteMessage: (msgId: string) => void;
  onOpenPhoto: (src: string, sender: string, time: string) => void;
  onReplyMessage?: (msg: ChatMessage) => void;
}

export function MessageList({
  messages,
  currentUser,
  onToggleReaction,
  onDeleteMessage,
  onOpenPhoto,
  onReplyMessage,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const lastTapRef = useRef<number>(0);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const formatTime = (ms: number) => {
    return new Date(ms).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true });
  };

  const formatDateLabel = (ms: number) => {
    const d = new Date(ms);
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);

    if (d.toDateString() === today.toDateString()) return "Today";
    if (d.toDateString() === yesterday.toDateString()) return "Yesterday";
    return d.toLocaleDateString([], { month: "short", day: "numeric", year: d.getFullYear() !== today.getFullYear() ? "numeric" : undefined });
  };

  const getStatusIcon = (status?: DeliveryStatus) => {
    if (status === "pending") return "🕒";
    if (status === "delivered" || status === "seen") return "✓✓";
    return "✓";
  };

  const handleBubbleClick = (msgId: string) => {
    const now = Date.now();
    if (now - lastTapRef.current < 300) {
      burstHearts(12);
      onToggleReaction(msgId, "❤️");
    }
    lastTapRef.current = now;
  };

  const toggleAudio = (msgId: string, src: string) => {
    if (playingAudioId === msgId) {
      audioPlayerRef.current?.pause();
      setPlayingAudioId(null);
    } else {
      if (!audioPlayerRef.current) {
        audioPlayerRef.current = new Audio();
      }
      audioPlayerRef.current.src = src;
      audioPlayerRef.current.onended = () => setPlayingAudioId(null);
      audioPlayerRef.current.play().catch(() => {});
      setPlayingAudioId(msgId);
    }
  };

  // Group messages by date
  let lastDateLabel = "";

  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-4 flex flex-col gap-2.5 sm:gap-3 bg-transparent">
      <div className="text-center text-xs text-[var(--text-sub)] py-2 px-4 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] max-w-sm mx-auto shadow-sm">
        🔒 Welcome to your private couple&apos;s space. Double-tap messages to send love! 💕
      </div>

      {messages.map((msg) => {
        const timeMs = Number(msg.time_ms) || Date.now();
        const dateLabel = formatDateLabel(timeMs);
        const showDivider = dateLabel !== lastDateLabel;
        if (showDivider) lastDateLabel = dateLabel;

        const isMine = msg.sender.toLowerCase() === currentUser.toLowerCase();

        return (
          <React.Fragment key={msg.id}>
            {showDivider && (
              <div className="text-center my-2">
                <span className="text-[10px] sm:text-xs font-bold uppercase tracking-wider text-[var(--text-sub)] bg-[var(--bg-card)] px-3 py-1 rounded-full border border-[var(--border)]">
                  {dateLabel}
                </span>
              </div>
            )}

            <div
              className={`flex items-end gap-2 max-w-[88%] sm:max-w-[75%] ${
                isMine ? "self-end flex-row-reverse" : "self-start"
              }`}
            >
              {/* Avatar initial */}
              <div
                className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-xs sm:text-sm font-bold shrink-0 border ${
                  isMine
                    ? "bg-[var(--accent-dim)] border-[var(--accent)] text-white"
                    : "bg-[var(--bg-card)] border-[var(--border)] text-[var(--text-main)]"
                }`}
              >
                {msg.sender.charAt(0).toUpperCase()}
              </div>

              {/* Message Bubble Column */}
              <div className="flex flex-col min-w-0">
                {/* Meta Row */}
                <div
                  className={`flex items-baseline gap-1.5 text-[10px] sm:text-xs text-[var(--text-sub)] mb-0.5 px-1 ${
                    isMine ? "justify-end" : "justify-start"
                  }`}
                >
                  <span className="font-semibold text-white/90">{msg.sender}</span>
                  <span>{formatTime(timeMs)}</span>
                  {isMine && (
                    <span
                      className={`text-[10px] font-bold tracking-tighter ${
                        msg.status === "seen"
                          ? "text-[var(--accent)]"
                          : msg.status === "delivered"
                          ? "text-white"
                          : "opacity-60"
                      }`}
                      title={msg.status}
                    >
                      {getStatusIcon(msg.status)}
                    </span>
                  )}
                </div>

                {/* Content Bubble */}
                <div
                  onClick={() => handleBubbleClick(msg.id)}
                  className={`relative group rounded-2xl px-3.5 py-2.5 shadow-sm text-sm sm:text-base leading-relaxed break-words select-text ${
                    isMine
                      ? "bg-[var(--mine-bg)] text-white rounded-br-sm"
                      : "bg-[var(--theirs-bg)] text-[var(--theirs-text)] border border-[var(--border)] rounded-bl-sm"
                  }`}
                >
                  {/* Replied Quote */}
                  {msg.reply_to && (
                    <div className="mb-2 px-2.5 py-1.5 rounded-lg bg-black/25 border-l-2 border-[var(--accent)] text-xs text-left max-w-full">
                      <div className="font-bold text-[var(--accent)] text-[11px] truncate">
                        {msg.reply_to.sender}
                      </div>
                      <div className="text-white/80 truncate text-[11px]">
                        {msg.reply_to.content || (msg.reply_to.type === "image" ? "📷 Live Moment" : msg.reply_to.type === "audio" ? "🎙️ Voice Note" : "Message")}
                      </div>
                    </div>
                  )}

                  {/* Photo with Photo-Shield */}
                  {msg.image && (
                    <div
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpenPhoto(msg.image!, msg.sender, formatTime(timeMs));
                      }}
                      className="relative overflow-hidden rounded-xl border border-white/10 mb-1 max-w-[240px] max-h-[200px] cursor-pointer"
                      onContextMenu={(e) => e.preventDefault()}
                    >
                      <div className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-sm text-[10px] text-white font-bold flex items-center gap-1 z-10">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                        Live Moment
                      </div>
                      <img
                        src={msg.image}
                        alt="Moment"
                        className="w-full h-full object-cover pointer-events-none"
                        draggable={false}
                      />
                      <div className="photo-shield" />
                    </div>
                  )}

                  {/* Audio Note */}
                  {msg.audio && (
                    <div className="flex items-center gap-3 py-1 min-w-[180px]">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleAudio(msg.id, msg.audio!);
                        }}
                        className="w-9 h-9 rounded-full bg-white/20 text-white flex items-center justify-center text-sm font-bold active:scale-95 transition-transform shrink-0"
                      >
                        {playingAudioId === msg.id ? "⏸" : "▶"}
                      </button>
                      <div className="flex flex-col flex-1">
                        <div className="flex items-center gap-1 h-3.5">
                          <span className="w-1 bg-white/70 h-2 rounded-full animate-pulse"></span>
                          <span className="w-1 bg-white/90 h-3 rounded-full animate-pulse"></span>
                          <span className="w-1 bg-white/60 h-1.5 rounded-full animate-pulse"></span>
                          <span className="w-1 bg-white h-3.5 rounded-full animate-pulse"></span>
                          <span className="w-1 bg-white/80 h-2.5 rounded-full animate-pulse"></span>
                        </div>
                        <span className="text-[10px] opacity-80 mt-1">
                          🎙️ Voice Note {msg.audio_duration ? `• ${msg.audio_duration}s` : ""}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Text Content */}
                  {msg.content && <div className="whitespace-pre-wrap">{msg.content}</div>}

                  {/* Hover Quick Actions */}
                  <div className="absolute -top-3 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-[var(--bg-card)] border border-[var(--border)] rounded-full px-1.5 py-0.5 shadow-lg flex items-center gap-1.5 text-xs z-10">
                    <button onClick={() => onReplyMessage?.(msg)} title="Reply" className="hover:scale-125 transition-transform text-white/90">↩️</button>
                    <button onClick={() => onToggleReaction(msg.id, "❤️")} className="hover:scale-125 transition-transform">❤️</button>
                    <button onClick={() => onToggleReaction(msg.id, "🥰")} className="hover:scale-125 transition-transform">🥰</button>
                    <button onClick={() => onToggleReaction(msg.id, "😂")} className="hover:scale-125 transition-transform">😂</button>
                    <button onClick={() => onToggleReaction(msg.id, "🥺")} className="hover:scale-125 transition-transform">🥺</button>
                    <button onClick={() => onDeleteMessage(msg.id)} className="hover:scale-125 transition-transform pl-1 text-red-400">🗑️</button>
                  </div>
                </div>

                {/* Reactions Pill Display */}
                {msg.reactions && Object.keys(msg.reactions).length > 0 && (
                  <div className={`flex flex-wrap gap-1 mt-1 px-1 ${isMine ? "justify-end" : "justify-start"}`}>
                    {Object.entries(msg.reactions).map(([emoji, users]) => (
                      <button
                        key={emoji}
                        onClick={() => onToggleReaction(msg.id, emoji)}
                        className={`text-xs px-2 py-0.5 rounded-full border flex items-center gap-1 active:scale-95 transition-transform ${
                          users.includes(currentUser)
                            ? "bg-[var(--accent-dim)] border-[var(--accent)] text-white"
                            : "bg-[var(--bg-card)] border-[var(--border)] text-[var(--text-main)]"
                        }`}
                      >
                        <span>{emoji}</span>
                        <span className="text-[10px] font-bold">{users.length}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </React.Fragment>
        );
      })}

      <div ref={bottomRef} />
    </div>
  );
}
