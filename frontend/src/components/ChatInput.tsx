"use client";

import React, { useState, useRef, useEffect } from "react";

interface ChatInputProps {
  onSendMessage: (content: string, stagedPhoto: string | null) => void;
  onSendAudio: (audioBase64: string, durationSec: number) => void;
  onSendNudge: () => void;
  nudgeCooldown: number;
}

export function ChatInput({
  onSendMessage,
  onSendAudio,
  onSendNudge,
  nudgeCooldown,
}: ChatInputProps) {
  const [text, setText] = useState("");
  const [stagedPhoto, setStagedPhoto] = useState<string | null>(null);

  // Camera state
  const [cameraOpen, setCameraOpen] = useState(false);
  const [facingMode, setFacingMode] = useState<"user" | "environment">("user");
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Audio recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordDuration, setRecordDuration] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Stop camera when modal closes
  useEffect(() => {
    if (!cameraOpen && streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, [cameraOpen]);

  const startCamera = async (mode: "user" | "environment") => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: mode, width: { ideal: 1080 }, height: { ideal: 1080 } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setFacingMode(mode);
      setCameraOpen(true);
    } catch {
      alert("Unable to open camera. Please allow camera permissions!");
    }
  };

  const captureLivePhoto = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 640;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    if (facingMode === "user") {
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.85);

    setStagedPhoto(dataUrl);
    setCameraOpen(false);
  };

  const flipCamera = () => {
    const nextMode = facingMode === "user" ? "environment" : "user";
    startCamera(nextMode);
  };

  // Audio recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
      setRecordDuration(0);

      recordIntervalRef.current = setInterval(() => {
        setRecordDuration((prev) => prev + 1);
      }, 1000);
    } catch {
      alert("Microphone permission required for voice notes!");
    }
  };

  const cancelRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach((t) => t.stop());
      clearInterval(recordIntervalRef.current!);
      setIsRecording(false);
      audioChunksRef.current = [];
    }
  };

  const sendRecording = () => {
    if (!mediaRecorderRef.current || !isRecording) return;
    const duration = recordDuration;
    mediaRecorderRef.current.onstop = () => {
      clearInterval(recordIntervalRef.current!);
      setIsRecording(false);

      const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
      const reader = new FileReader();
      reader.onload = (e) => {
        const base64 = e.target?.result as string;
        onSendAudio(base64, duration);
      };
      reader.readAsDataURL(blob);
    };

    mediaRecorderRef.current.stop();
    mediaRecorderRef.current.stream.getTracks().forEach((t) => t.stop());
  };

  const handleSend = () => {
    if (!text.trim() && !stagedPhoto) return;
    onSendMessage(text.trim(), stagedPhoto);
    setText("");
    setStagedPhoto(null);
  };

  return (
    <div className="p-2 sm:p-3 bg-[var(--bg-dark)] border-t border-[var(--border)] shrink-0 z-10">
      {/* Audio Recording Live Panel */}
      {isRecording && (
        <div className="flex items-center justify-between px-3 py-2 bg-[var(--bg-card)] rounded-xl border border-[var(--border)] mb-2 animate-pulse">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping"></span>
            <span className="text-xs font-bold text-white">Recording Voice Note...</span>
            <span className="text-xs text-[var(--accent)] font-mono font-bold">
              {Math.floor(recordDuration / 60)}:{(recordDuration % 60).toString().padStart(2, "0")}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={cancelRecording}
              className="px-2.5 py-1 text-xs text-white/70 hover:text-white"
            >
              Cancel
            </button>
            <button
              onClick={sendRecording}
              className="px-3 py-1 bg-[var(--accent)] text-white text-xs font-bold rounded-lg shadow-sm"
            >
              Send 🎙️
            </button>
          </div>
        </div>
      )}

      {/* Staged Photo Preview */}
      {stagedPhoto && (
        <div className="relative inline-block mb-2 rounded-xl overflow-hidden border border-[var(--accent)] shadow-md">
          <img src={stagedPhoto} alt="Captured" className="w-20 h-20 object-cover" />
          <button
            onClick={() => setStagedPhoto(null)}
            className="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/70 text-white text-[10px] flex items-center justify-center font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Bottom Tool Row */}
      <div className="flex items-center gap-1.5 sm:gap-2">
        {/* Live Camera Button */}
        <button
          onClick={() => startCamera(facingMode)}
          className="w-10 h-10 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text-main)] flex items-center justify-center text-lg shrink-0 active:scale-95 transition-transform"
          title="Take Live Photo (Live camera only)"
        >
          📷
        </button>

        {/* Voice Note Button */}
        <button
          onClick={startRecording}
          disabled={isRecording}
          className="w-10 h-10 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text-main)] flex items-center justify-center text-lg shrink-0 active:scale-95 transition-transform"
          title="Record Voice Note"
        >
          🎙️
        </button>

        {/* Input Text Box */}
        <div className="flex-1 relative">
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSend();
            }}
            placeholder="Write something sweet..."
            className="w-full bg-[var(--bg-card)] border border-[var(--border)] rounded-xl px-3.5 py-2.5 text-base sm:text-sm text-[var(--text-main)] placeholder-[var(--text-sub)]/60 focus:outline-none focus:border-[var(--accent)] transition-colors"
          />
        </div>

        {/* Love Nudge / Thinking of You Shortcut */}
        <button
          onClick={onSendNudge}
          disabled={nudgeCooldown > 0}
          className={`w-10 h-10 rounded-xl border flex items-center justify-center text-base shrink-0 active:scale-95 transition-transform ${
            nudgeCooldown > 0
              ? "bg-[var(--bg-card)] border-[var(--border)] text-[var(--accent)] font-black text-xs cursor-not-allowed opacity-75"
              : "bg-[var(--accent-dim)] border-[var(--accent)] text-[var(--accent)]"
          }`}
          title="Thinking of You! 💖"
        >
          {nudgeCooldown > 0 ? `${nudgeCooldown}s` : "💖"}
        </button>

        {/* Send Button */}
        <button
          onClick={handleSend}
          className="h-10 px-4 rounded-xl bg-[var(--mine-bg)] text-white text-sm font-bold flex items-center justify-center shrink-0 shadow-sm active:scale-95 transition-transform"
        >
          <span>Send</span>
        </button>
      </div>

      {/* Live Camera Modal (No gallery access, live snapshot only) */}
      {cameraOpen && (
        <div className="fixed inset-0 bg-black/95 z-50 flex flex-col items-center justify-between p-4">
          <div className="w-full flex items-center justify-between text-white text-sm font-bold px-2">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              Live Camera Moment
            </span>
            <button
              onClick={() => setCameraOpen(false)}
              className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center"
            >
              ✕
            </button>
          </div>

          <div className="relative w-full max-w-sm aspect-square rounded-2xl overflow-hidden border-2 border-[var(--accent)] bg-black">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className={`w-full h-full object-cover ${facingMode === "user" ? "scale-x-[-1]" : ""}`}
            />
          </div>

          <div className="flex items-center gap-8 mb-6">
            <button
              onClick={flipCamera}
              className="w-12 h-12 rounded-full bg-white/20 text-white flex items-center justify-center text-xl"
              title="Flip Camera"
            >
              🔄
            </button>

            <button
              onClick={captureLivePhoto}
              className="w-18 h-18 rounded-full border-4 border-white bg-[var(--accent)] shadow-lg active:scale-90 transition-transform flex items-center justify-center text-2xl"
              title="Capture Moment"
            >
              📸
            </button>

            <button
              onClick={() => setCameraOpen(false)}
              className="w-12 h-12 rounded-full bg-white/20 text-white flex items-center justify-center text-sm font-bold"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
