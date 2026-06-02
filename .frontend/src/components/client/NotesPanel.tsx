"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { addRecoveryNote } from "@/lib/api";
import type { RecoveryNote } from "@/lib/types";
import { formatDateShort } from "@/lib/formatters";

interface NotesPanelProps {
  notes: RecoveryNote[];
  athleteId: string;
  onNoteAdded: () => void;
  onConfirm: (text: string, action: () => Promise<void>) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export default function NotesPanel({ notes, athleteId, onNoteAdded, onConfirm, collapsed, onToggleCollapse }: NotesPanelProps) {
  const [dateFilter, setDateFilter] = useState<string>("all");
  const [rType, setRType] = useState("note");
  const [rContent, setRContent] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const uniqueDates = [...new Set(notes.map((n) => n.created_at.slice(0, 10)))].sort().reverse();

  const filtered = dateFilter === "all"
    ? notes
    : notes.filter((n) => n.created_at.startsWith(dateFilter));

  const handleSave = () => {
    if (!rContent.trim()) return;
    const rendered = `Recovery note (${rType}): ${rContent}`;
    onConfirm(rendered, async () => {
      setSubmitting(true);
      await addRecoveryNote("coach-001", athleteId, { note_type: rType, content: rContent });
      setRContent("");
      setSubmitting(false);
      onNoteAdded();
    });
  };

  if (collapsed) {
    return (
      <aside
        className="fixed right-0 top-0 bottom-0 w-10 flex flex-col items-center z-20 border-l cursor-pointer"
        style={{ background: "var(--color-bg-card)", borderColor: "var(--color-border-light)" }}
        onClick={onToggleCollapse}
      >
        <div className="mt-4 flex flex-col items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.5" strokeLinecap="round"><path d="M10 4l-4 4 4 4" /></svg>
          <span className="text-[10px] font-medium" style={{ writingMode: "vertical-rl", color: "var(--color-text-muted)" }}>Notes</span>
          {notes.length > 0 && (
            <span className="text-[9px] w-4 h-4 rounded-full flex items-center justify-center" style={{ background: "var(--color-accent-light)", color: "var(--color-accent-primary)" }}>{notes.length}</span>
          )}
        </div>
      </aside>
    );
  }

  return (
    <aside
      className="fixed right-0 top-0 bottom-0 w-80 flex flex-col z-20 border-l"
      style={{ background: "var(--color-bg-card)", borderColor: "var(--color-border-light)" }}
    >
      {/* Header */}
      <div className="px-5 py-4 border-b shrink-0" style={{ borderColor: "var(--color-border-card)" }}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold" style={{ fontFamily: "'Crimson Pro', serif" }}>Notes</h2>
          <div className="flex items-center gap-2">
            <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "var(--color-bg-secondary)", color: "var(--color-text-muted)" }}>{notes.length}</span>
            <button onClick={onToggleCollapse} className="p-1 rounded hover:opacity-70" title="Collapse notes">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.5" strokeLinecap="round"><path d="M4 7h6M9 4l3 3-3 3" /></svg>
            </button>
          </div>
        </div>
        <select
          value={dateFilter}
          onChange={(e) => setDateFilter(e.target.value)}
          className="w-full text-xs px-2.5 py-1.5 rounded-lg border"
          style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-secondary)" }}
        >
          <option value="all">All notes</option>
          {uniqueDates.map((d) => (
            <option key={d} value={d}>{formatDateShort(d)}</option>
          ))}
        </select>
      </div>

      {/* Notes list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2.5">
        <AnimatePresence>
          {filtered.map((note) => (
            <motion.div
              key={note.id}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="rounded-lg p-3 border"
              style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-primary)" }}
            >
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="text-[10px] font-medium px-1.5 py-0.5 rounded capitalize"
                  style={{ background: "var(--color-accent-light)", color: "var(--color-accent-primary)" }}
                >
                  {note.note_type.replace(/_/g, " ")}
                </span>
                <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>
                  {formatDateShort(note.created_at)}
                </span>
              </div>
              <p className="text-xs leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{note.content}</p>
            </motion.div>
          ))}
        </AnimatePresence>
        {filtered.length === 0 && (
          <p className="text-xs text-center py-6" style={{ color: "var(--color-text-muted)" }}>No notes{dateFilter !== "all" ? " for this date" : ""}</p>
        )}
      </div>

      {/* Add note form — always visible at bottom */}
      <div className="shrink-0 px-4 py-3 border-t space-y-2" style={{ borderColor: "var(--color-border-card)" }}>
        <select
          value={rType}
          onChange={(e) => setRType(e.target.value)}
          className="w-full text-xs px-2.5 py-1.5 rounded-lg border"
          style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }}
        >
          <option value="note">Note</option>
          <option value="sleep">Sleep</option>
          <option value="deload">Deload</option>
          <option value="rest_day">Rest Day</option>
          <option value="active_recovery">Active Recovery</option>
        </select>
        <textarea
          value={rContent}
          onChange={(e) => setRContent(e.target.value)}
          placeholder="Add a note..."
          rows={2}
          className="w-full text-xs px-2.5 py-1.5 rounded-lg border resize-none"
          style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }}
        />
        <button
          onClick={handleSave}
          disabled={!rContent.trim() || submitting}
          className="w-full text-xs font-medium py-1.5 rounded-lg text-white disabled:opacity-40"
          style={{ background: "var(--color-accent-primary)" }}
        >
          {submitting ? "Saving..." : "Add Note"}
        </button>
      </div>
    </aside>
  );
}
