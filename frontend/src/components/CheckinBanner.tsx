"use client";

import React from "react";
import { CheckInDoc } from "@/lib/types";

interface CheckinBannerProps {
  partnerCheckin: CheckInDoc | null;
  onOpenCheckIn: () => void;
}

export function CheckinBanner({ partnerCheckin, onOpenCheckIn }: CheckinBannerProps) {
  const formatTime = (ms: number) => {
    return new Date(ms).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", hour12: true });
  };

  return (
    <div
      onClick={onOpenCheckIn}
      className="bg-gradient-to-r from-[var(--accent-dim)] to-transparent border-b border-[var(--border)] px-3.5 py-2 flex items-center justify-between cursor-pointer active:bg-[var(--accent-dim)] transition-colors shrink-0 z-9"
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <div className="w-8 h-8 rounded-full bg-[var(--bg-card)] border border-[var(--accent)] flex items-center justify-center text-lg shrink-0 shadow-sm">
          {partnerCheckin ? partnerCheckin.mood : "🥰"}
        </div>
        <div className="flex flex-col min-w-0">
          <div className="text-xs sm:text-sm font-bold text-white truncate">
            {partnerCheckin
              ? `${partnerCheckin.username}: ${partnerCheckin.mood} ${partnerCheckin.note ? `"${partnerCheckin.note}"` : ""}`
              : "Daily Check-In: How was your day?"}
          </div>
          <div className="text-[11px] text-[var(--text-sub)] truncate">
            {partnerCheckin
              ? `Updated today at ${formatTime(partnerCheckin.updated_at)} 💕`
              : "Tap to share your mood & see hers 💕"}
          </div>
        </div>
      </div>
      <span className="text-base font-extrabold text-[var(--accent)] pr-1">›</span>
    </div>
  );
}
