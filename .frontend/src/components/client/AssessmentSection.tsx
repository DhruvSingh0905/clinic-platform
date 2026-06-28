"use client";

import { useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { formatDate } from "@/lib/formatters";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface Assessment {
  id: string;
  note_type: string;
  content: string;
  created_at: string;
}

interface AssessmentSectionProps {
  patientId: string;
  notes: Assessment[];
  onNoteAdded: () => void;
}

const NOTE_TYPES = [
  { value: "assessment", label: "Assessment" },
  { value: "plan", label: "Plan" },
  { value: "subjective", label: "Subjective" },
  { value: "objective", label: "Objective" },
  { value: "follow_up", label: "Follow-up Note" },
  { value: "general", label: "General" },
];

export default function AssessmentSection({ patientId, notes, onNoteAdded }: AssessmentSectionProps) {
  const [noteType, setNoteType] = useState("assessment");
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);

  const filtered = search
    ? notes.filter((n) => n.content.toLowerCase().includes(search.toLowerCase()) || n.note_type.toLowerCase().includes(search.toLowerCase()))
    : notes;

  const handleSave = async () => {
    if (!content.trim()) return;
    setSubmitting(true);
    try {
      await fetch(`${API}/api/clinician/clinician-001/patient/${patientId}/recovery`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note_type: noteType, content }),
      });
      setContent("");
      setShowForm(false);
      onNoteAdded();
    } catch {}
    setSubmitting(false);
  };

  const typeColor = (type: string) => {
    switch (type) {
      case "assessment": return { bg: "var(--color-accent-light)", text: "var(--color-accent-primary)" };
      case "plan": return { bg: "var(--color-success-bg)", text: "var(--color-success)" };
      case "subjective": return { bg: "var(--color-severity-notable-bg)", text: "var(--color-severity-notable)" };
      case "objective": return { bg: "var(--color-severity-info-bg)", text: "var(--color-severity-info)" };
      case "follow_up": return { bg: "var(--color-severity-concerning-bg)", text: "var(--color-severity-concerning)" };
      default: return { bg: "var(--color-bg-hover)", text: "var(--color-text-muted)" };
    }
  };

  return (
    <div className="space-y-3">
      {/* Header with search + add */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search notes..."
          className="text-xs px-3 py-1.5 flex-1 border"
          style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }}
        />
        <button onClick={() => setShowForm(!showForm)} className="text-[10px] font-medium px-3 py-1.5 text-white shrink-0" style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}>
          {showForm ? "Cancel" : "+ New Note"}
        </button>
      </div>

      {/* New note form */}
      <AnimatePresence>
        {showForm && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="border p-3 space-y-2" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
              <div className="flex gap-2">
                {NOTE_TYPES.map((t) => {
                  const c = typeColor(t.value);
                  return (
                    <button key={t.value} onClick={() => setNoteType(t.value)} className="text-[9px] font-medium px-2 py-1 uppercase" style={{ background: noteType === t.value ? c.bg : "var(--color-bg-hover)", color: noteType === t.value ? c.text : "var(--color-text-muted)", borderRadius: "2px" }}>
                      {t.label}
                    </button>
                  );
                })}
              </div>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Clinical note..."
                rows={4}
                className="w-full text-xs px-3 py-2 border resize-none"
                style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }}
              />
              <button onClick={handleSave} disabled={!content.trim() || submitting} className="text-[10px] font-medium px-4 py-1.5 text-white disabled:opacity-30" style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}>
                {submitting ? "Saving..." : "Save Note"}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Notes list */}
      {filtered.length === 0 && <p className="text-xs py-6 text-center" style={{ color: "var(--color-text-muted)" }}>No clinical notes yet.</p>}

      {filtered.length > 0 && (
        <div className="space-y-2">
          {filtered.map((note) => {
            const c = typeColor(note.note_type);
            return (
              <div key={note.id} className="border p-3" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-[9px] font-medium px-1.5 py-0.5 uppercase" style={{ background: c.bg, color: c.text, borderRadius: "2px" }}>
                    {note.note_type.replace(/_/g, " ")}
                  </span>
                  <span className="text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{formatDate(note.created_at)}</span>
                </div>
                <p className="text-xs leading-relaxed whitespace-pre-wrap" style={{ color: "var(--color-text-secondary)" }}>{note.content}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
