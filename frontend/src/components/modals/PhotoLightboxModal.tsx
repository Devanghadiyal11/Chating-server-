"use client";

import React from "react";

interface PhotoLightboxModalProps {
  photo: { src: string; sender: string; time: string } | null;
  onClose: () => void;
}

export function PhotoLightboxModal({ photo, onClose }: PhotoLightboxModalProps) {
  if (!photo) return null;

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 bg-black/95 z-50 flex flex-col items-center justify-center p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative max-w-[92vw] max-h-[85vh] flex flex-col items-center"
      >
        <div className="relative overflow-hidden rounded-2xl border border-white/20 shadow-2xl">
          <img
            src={photo.src}
            alt="Captured Moment"
            className="max-w-full max-h-[70vh] object-contain pointer-events-none"
            draggable={false}
          />
          <div className="photo-shield" onContextMenu={(e) => e.preventDefault()} />
        </div>

        <div className="mt-3 text-center text-white">
          <div className="text-sm font-bold">Captured live by {photo.sender} 💕</div>
          <div className="text-xs text-[var(--text-sub)] mt-0.5">{photo.time}</div>
        </div>

        <button
          onClick={onClose}
          className="mt-4 px-5 py-1.5 rounded-full bg-white/20 hover:bg-white/30 text-white text-xs font-bold transition-colors"
        >
          ✕ Close
        </button>
      </div>
    </div>
  );
}
