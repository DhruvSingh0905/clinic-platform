"use client";

import { useState, useEffect } from "react";
import { formatDate } from "@/lib/formatters";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface FollowUp {
  id: number;
  event_type: string;
  scheduled_date: string;
  scheduled_time: string | null;
  description: string | null;
  status: string;
}

interface FollowUpSectionProps {
  patientId: string;
}

export default function FollowUpSection({ patientId }: FollowUpSectionProps) {
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const load = () => {
    fetch(`${API}/api/clinician/clinician-001/patient/${patientId}/checkins`)
      .then((r) => r.json())
      .then((d) => setFollowUps(d.checkins || []))
      .catch(() => {});
  };

  useEffect(() => { load(); }, [patientId]);

  const handleSchedule = async () => {
    if (!date) return;
    setSubmitting(true);
    try {
      await fetch(`${API}/api/clinician/clinician-001/patient/${patientId}/schedule/checkin`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date, time: time || null, description: description || "Follow-up appointment" }),
      });
      setDate(""); setTime(""); setDescription(""); setShowForm(false);
      load();
    } catch {}
    setSubmitting(false);
  };

  const upcoming = followUps.filter((f) => f.status === "upcoming");
  const past = followUps.filter((f) => f.status !== "upcoming");

  return (
    <div className="space-y-4">
      {/* Schedule button */}
      <button onClick={() => setShowForm(!showForm)} className="text-[10px] font-medium px-3 py-1.5 text-white" style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}>
        {showForm ? "Cancel" : "+ Schedule Follow-up"}
      </button>

      {/* Schedule form */}
      {showForm && (
        <div className="border p-3 space-y-2" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Date *</label>
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }} />
            </div>
            <div>
              <label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Time</label>
              <input type="time" value={time} onChange={(e) => setTime(e.target.value)} className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }} />
            </div>
          </div>
          <div>
            <label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Description</label>
            <input type="text" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Follow-up reason" className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }} />
          </div>
          <button onClick={handleSchedule} disabled={!date || submitting} className="text-[10px] font-medium px-4 py-1.5 text-white disabled:opacity-30" style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}>
            {submitting ? "Scheduling..." : "Schedule"}
          </button>
        </div>
      )}

      {/* Upcoming */}
      {upcoming.length > 0 && (
        <div>
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-text-muted)" }}>Upcoming</h3>
          <div className="border overflow-hidden" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
            {upcoming.map((f, i) => (
              <div key={f.id}>
                {i > 0 && <div style={{ borderTop: "1px solid var(--color-border-light)" }} />}
                <div className="px-3 py-2.5 flex items-center gap-3">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ background: "var(--color-accent-primary)" }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium">{f.description || "Follow-up"}</p>
                    <p className="text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>
                      {formatDate(f.scheduled_date)}{f.scheduled_time ? ` at ${f.scheduled_time}` : ""}
                    </p>
                  </div>
                  <span className="text-[9px] font-medium px-1.5 py-0.5 uppercase" style={{ background: "var(--color-accent-light)", color: "var(--color-accent-primary)", borderRadius: "2px" }}>Upcoming</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Past */}
      {past.length > 0 && (
        <div>
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-text-muted)" }}>Past</h3>
          <div className="border overflow-hidden" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
            {past.map((f, i) => (
              <div key={f.id}>
                {i > 0 && <div style={{ borderTop: "1px solid var(--color-border-light)" }} />}
                <div className="px-3 py-2 flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs">{f.description || "Follow-up"}</p>
                    <p className="text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{formatDate(f.scheduled_date)}</p>
                  </div>
                  <span className="text-[9px] px-1.5 py-0.5 uppercase" style={{ background: "var(--color-bg-hover)", color: "var(--color-text-muted)", borderRadius: "2px" }}>{f.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {followUps.length === 0 && !showForm && <p className="text-xs py-6 text-center" style={{ color: "var(--color-text-muted)" }}>No follow-ups scheduled.</p>}
    </div>
  );
}
