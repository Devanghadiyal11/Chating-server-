"use client";

import React, { useState, useEffect } from "react";
import { TimelineEvent } from "@/lib/types";

interface TimelineModalProps {
  isOpen: boolean;
  onClose: () => void;
  daysTogether: number;
  anniversaryDate: string;
  timeline: TimelineEvent[];
  onAddMilestone: (event: Omit<TimelineEvent, "id">) => void;
  onDeleteMilestone: (id: string) => void;
}

export function TimelineModal({
  isOpen,
  onClose,
  daysTogether,
  anniversaryDate,
  timeline,
  onAddMilestone,
  onDeleteMilestone,
}: TimelineModalProps) {
  const [showAdd, setShowAdd] = useState(false);
  const [icon, setIcon] = useState("💖");
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (isOpen && !date) {
      setDate(new Date().toISOString().split("T")[0]);
    }
  }, [isOpen, date]);

  if (!isOpen) return null;

  // Calculate next anniversary
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const anniv = new Date(anniversaryDate || "2024-02-14");
  let nextAnniv = new Date(today.getFullYear(), anniv.getMonth(), anniv.getDate());
  if (nextAnniv < today) {
    nextAnniv.setFullYear(today.getFullYear() + 1);
  }
  const daysUntilNext = Math.ceil((nextAnniv.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

  const handleSave = () => {
    if (!title.trim() || !date) return alert("Please enter title and date!");
    onAddMilestone({ icon: icon || "💖", title: title.trim(), date, notes: notes.trim() });
    setTitle("");
    setNotes("");
    setShowAdd(false);
  };

  const getRelativeBadge = (dateStr: string) => {
    const itemDate = new Date(dateStr);
    itemDate.setHours(0, 0, 0, 0);
    const diffDays = Math.round((itemDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today! 🎉";
    if (diffDays > 0) return `In ${diffDays}d ✨`;
    return `${Math.abs(diffDays)}d ago 💕`;
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-xs z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
      <div className="w-full sm:max-w-lg bg-[var(--bg-card)] border border-[var(--border)] rounded-t-3xl sm:rounded-3xl overflow-hidden shadow-2xl animate-in fade-in slide-in-from-bottom-6 duration-200 flex flex-col max-h-[85vh]">
        <div className="p-5 bg-[var(--mine-bg)] text-white text-center shrink-0">
          <div className="text-3xl mb-1">⏳</div>
          <h2 className="text-lg font-extrabold">Our Relationship Timeline</h2>
          <p className="text-xs opacity-90">Meaningful dates & live shared countdowns</p>
        </div>

        <div className="p-4 flex-1 overflow-y-auto flex flex-col gap-3.5">
          {/* Top Counters */}
          <div className="grid grid-cols-2 gap-2.5">
            <div className="p-3 rounded-2xl bg-[var(--bg-root)] border border-dashed border-[var(--accent)] text-center">
              <div className="text-xl sm:text-2xl font-black text-[var(--accent)]">{daysTogether}</div>
              <div className="text-[11px] text-[var(--text-sub)] font-semibold mt-0.5">Days Loving You 💕</div>
            </div>

            <div className="p-3 rounded-2xl bg-[var(--bg-root)] border border-dashed border-[var(--accent)] text-center">
              <div className="text-xl sm:text-2xl font-black text-[var(--accent)]">{daysUntilNext}d</div>
              <div className="text-[11px] text-[var(--text-sub)] font-semibold mt-0.5">Next Anniversary 💍</div>
            </div>
          </div>

          {/* Add Milestone Collapsible Form */}
          {showAdd ? (
            <div className="p-3 rounded-2xl bg-[var(--bg-root)] border border-[var(--border)] flex flex-col gap-2">
              <div className="text-xs font-bold text-white uppercase tracking-wider">Add New Special Moment</div>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={icon}
                  onChange={(e) => setIcon(e.target.value)}
                  maxLength={2}
                  className="w-12 text-center bg-[var(--bg-card)] border border-[var(--border)] rounded-xl px-2 py-2 text-lg focus:outline-none focus:border-[var(--accent)]"
                />
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Moment title (e.g. Goa Trip)"
                  className="flex-1 bg-[var(--bg-card)] border border-[var(--border)] rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--accent)]"
                />
              </div>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--accent)]"
              />
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Optional sweet note..."
                className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-[var(--accent)]"
              />
              <div className="flex gap-2 mt-1">
                <button
                  onClick={handleSave}
                  className="flex-1 py-2 rounded-xl bg-[var(--accent)] text-white text-xs font-bold shadow-sm"
                >
                  Save Moment ✨
                </button>
                <button
                  onClick={() => setShowAdd(false)}
                  className="px-3 py-2 rounded-xl bg-[var(--bg-card)] border border-[var(--border)] text-xs text-white"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <span className="text-xs font-extrabold uppercase text-[var(--text-sub)] tracking-wider">Milestones</span>
              <button
                onClick={() => setShowAdd(true)}
                className="px-3 py-1 rounded-xl bg-[var(--accent-dim)] border border-[var(--accent)] text-[var(--accent)] text-xs font-bold active:scale-95 transition-transform"
              >
                + Add Milestone
              </button>
            </div>
          )}

          {/* Milestones List */}
          <div className="flex flex-col gap-2">
            {timeline.length === 0 ? (
              <div className="text-center py-6 text-xs text-[var(--text-sub)]">No milestones added yet 💕</div>
            ) : (
              timeline.map((item) => (
                <div
                  key={item.id}
                  className="p-3 rounded-2xl bg-[var(--bg-root)] border border-[var(--border)] flex items-center justify-between gap-3 shadow-xs"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-[var(--accent-dim)] border border-[var(--accent)] flex items-center justify-center text-lg shrink-0">
                      {item.icon || "💍"}
                    </div>
                    <div className="min-w-0">
                      <div className="text-sm font-bold text-white truncate">{item.title}</div>
                      <div className="text-[11px] text-[var(--text-sub)] truncate">
                        {item.date} {item.notes ? `• ${item.notes}` : ""}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] font-extrabold px-2.5 py-1 rounded-full bg-[var(--mine-bg)] text-white shadow-xs">
                      {getRelativeBadge(item.date)}
                    </span>
                    {!item.id.startsWith("t_") && (
                      <button
                        onClick={() => onDeleteMilestone(item.id)}
                        className="text-xs text-red-400 hover:text-red-300 p-1"
                        title="Delete"
                      >
                        🗑️
                      </button>
                    )}
                  </div>
                </div>
              ))
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
