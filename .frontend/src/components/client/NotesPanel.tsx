"use client";

import { useState } from "react";
import { addRecoveryNote } from "@/lib/api";
import type { RecoveryNote } from "@/lib/types";
import { formatDateShort } from "@/lib/formatters";

interface NotesPanelProps {
  notes: RecoveryNote[];
  patientId: string;
  onNoteAdded: () => void;
  onConfirm: (text: string, action: () => Promise<void>) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export default function NotesPanel({ notes, patientId, onNoteAdded, onConfirm, collapsed, onToggleCollapse }: NotesPanelProps) {
  const [dateFilter, setDateFilter] = useState<string>("all");
  const [rType, setRType] = useState("assessment");
  const [rContent, setRContent] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const uniqueDates = [...new Set(notes.map((n) => n.created_at.slice(0, 10)))].sort().reverse();
  const filtered = dateFilter === "all" ? notes : notes.filter((n) => n.created_at.startsWith(dateFilter));

  const handleSave = () => {
    if (!rContent.trim()) return;
    const rendered = `Recovery note (${rType}): ${rContent}`;
    onConfirm(rendered, async () => {
      setSubmitting(true);
      await addRecoveryNote("clinician-001", patientId, { note_type: rType, content: rContent });
      setRContent("");
      setSubmitting(false);
      onNoteAdded();
    });
  };

  if (collapsed) {
    return (
      <aside
        className="fixed right-0 top-0 bottom-0 w-8 flex flex-col items-center z-20 border-l cursor-pointer"
        style={{ background: "var(--color-bg-secondary)", borderColor: "var(--color-border-light)" }}
        onClick={onToggleCollapse}
      >
        <div className="mt-3 flex flex-col items-center gap-1.5">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.5" strokeLinecap="round"><path d="M8 3l-4 3 4 3" /></svg>
          <span className="text-[9px] font-medium uppercase tracking-wider" style={{ writingMode: "vertical-rl", color: "var(--color-text-muted)" }}>Notes</span>
          {notes.length > 0 && (
            <span className="text-[9px] font-medium" style={{ color: "var(--color-accent-primary)" }}>{notes.length}</span>
          )}
        </div>
      </aside>
    );
  }

  return (
    <aside
      className="fixed right-0 top-0 bottom-0 w-72 flex flex-col z-20 border-l"
      style={{ background: "var(--color-bg-secondary)", borderColor: "var(--color-border-light)" }}
    >
      {/* Header */}
      <div className="px-3 py-3 border-b shrink-0" style={{ borderColor: "var(--color-border-light)" }}>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--color-text-secondary)" }}>Notes</h2>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-medium" style={{ color: "var(--color-text-muted)", fontFamily: "'IBM Plex Mono', monospace" }}>{notes.length}</span>
            <button onClick={onToggleCollapse} className="p-0.5 hover:opacity-70" title="Collapse notes">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.5" strokeLinecap="round"><path d="M3 6h6M7 3l3 3-3 3" /></svg>
            </button>
          </div>
        </div>
        <select
          value={dateFilter}
          onChange={(e) => setDateFilter(e.target.value)}
          className="w-full text-[10px] px-2 py-1 border"
          style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-secondary)", borderRadius: "3px" }}
        >
          <option value="all">All notes</option>
          {uniqueDates.map((d) => (<option key={d} value={d}>{formatDateShort(d)}</option>))}
        </select>
      </div>

      {/* Notes list */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1.5">
        {filtered.map((note) => (
          <div key={note.id} className="p-2 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
            <div className="flex items-center gap-1.5 mb-1">
              <span className="text-[9px] font-medium uppercase tracking-wide px-1 py-0.5" style={{ background: "var(--color-accent-light)", color: "var(--color-accent-primary)", borderRadius: "2px" }}>
                {note.note_type.replace(/_/g, " ")}
              </span>
              <span className="text-[9px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{formatDateShort(note.created_at)}</span>
            </div>
            <p className="text-[11px] leading-relaxed" style={{ color: "var(--color-text-secondary)" }}>{note.content}</p>
          </div>
        ))}
        {filtered.length === 0 && (
          <p className="text-[10px] text-center py-4" style={{ color: "var(--color-text-muted)" }}>No notes{dateFilter !== "all" ? " for this date" : ""}</p>
        )}
      </div>

      {/* Add note */}
      <div className="shrink-0 px-3 py-2 border-t space-y-1.5" style={{ borderColor: "var(--color-border-light)" }}>
        <select
          value={rType}
          onChange={(e) => setRType(e.target.value)}
          className="w-full text-[10px] px-2 py-1 border"
          style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-secondary)", borderRadius: "3px" }}
        >
          <option value="assessment">Assessment</option>
          <option value="plan">Plan</option>
          <option value="subjective">Subjective</option>
          <option value="objective">Objective</option>
          <option value="follow_up">Follow-up Note</option>
          <option value="general">General</option>
        </select>
        <textarea
          value={rContent}
          onChange={(e) => setRContent(e.target.value)}
          placeholder="Add a note..."
          rows={2}
          className="w-full text-[11px] px-2 py-1.5 border resize-none"
          style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }}
        />
        <button
          onClick={handleSave}
          disabled={!rContent.trim() || submitting}
          className="w-full text-[10px] font-medium py-1.5 text-white disabled:opacity-30"
          style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}
        >
          {submitting ? "Saving..." : "Add Note"}
        </button>
      </div>
    </aside>
  );
}
