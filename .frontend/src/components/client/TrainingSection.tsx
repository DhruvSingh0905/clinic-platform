"use client";

import { useState, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { formatDate } from "@/lib/formatters";

interface TrainingSectionProps {
  training: { id: string; name: string; start_date: string; end_date: string | null; notes: string | null; status: string }[];
  patientId: string;
  onEditBlock: () => void;
}

interface ActivityEntry {
  id: string;
  title: string;
  date: string;
  duration_min: number;
  exercises: { name: string; sets: { weight_kg: number; reps: number; type: string }[] }[];
}

export default function TrainingSection({ training, patientId, onEditBlock }: TrainingSectionProps) {
  const [activities, setActivities] = useState<ActivityEntry[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState(28);

  const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

  useEffect(() => {
    fetch(`${API}/api/clinician/clinician-001/patient/${patientId}/workouts?days=${timeRange}`)
      .then((r) => r.json()).then((d) => setActivities(d.workouts || [])).catch(() => {});
  }, [patientId, timeRange, API]);

  const activeBlock = training.find((t) => t.status === "active");

  return (
    <div className="space-y-4">
      {activeBlock && (
        <div className="border p-3" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-semibold">{activeBlock.name}</span>
            <span className="text-[9px] font-medium px-1.5 py-0.5" style={{ background: "var(--color-success-bg)", color: "var(--color-success)", borderRadius: "2px" }}>Active</span>
            <span className="text-[10px] ml-auto" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{formatDate(activeBlock.start_date)}</span>
          </div>
          {activeBlock.notes && <p className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>{activeBlock.notes}</p>}
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>Activity Log</h3>
          <div className="flex gap-1">
            {[14, 28, 56].map((d) => (
              <button key={d} onClick={() => setTimeRange(d)} className="text-[9px] px-1.5 py-0.5" style={{ background: timeRange === d ? "var(--color-accent-light)" : "var(--color-bg-hover)", color: timeRange === d ? "var(--color-accent-primary)" : "var(--color-text-muted)", borderRadius: "2px" }}>
                {d === 14 ? "2wk" : d === 28 ? "4wk" : "8wk"}
              </button>
            ))}
          </div>
        </div>

        {activities.length === 0 && <p className="text-xs py-6 text-center" style={{ color: "var(--color-text-muted)" }}>No activity logged in this period.</p>}

        {activities.length > 0 && (
          <div className="border overflow-hidden" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
            <div className="grid grid-cols-12 gap-2 px-3 py-1.5 text-[9px] font-medium uppercase tracking-wider border-b" style={{ color: "var(--color-text-muted)", borderColor: "var(--color-border-light)" }}>
              <div className="col-span-2">Date</div>
              <div className="col-span-6">Activity</div>
              <div className="col-span-2">Duration</div>
              <div className="col-span-2 text-right">Exercises</div>
            </div>
            {activities.map((a) => (
              <div key={a.id}>
                <button onClick={() => setExpanded(expanded === a.id ? null : a.id)} className="w-full grid grid-cols-12 gap-2 items-center px-3 py-2 text-left data-row border-b" style={{ borderColor: "var(--color-border-light)" }}>
                  <span className="col-span-2 text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{a.date.slice(5)}</span>
                  <span className="col-span-6 text-xs font-medium truncate">{a.title}</span>
                  <span className="col-span-2 text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{a.duration_min}min</span>
                  <span className="col-span-2 text-right text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{a.exercises.length}</span>
                </button>
                <AnimatePresence>
                  {expanded === a.id && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.15 }} className="overflow-hidden">
                      <div className="px-3 py-2" style={{ background: "var(--color-bg-secondary)" }}>
                        {a.exercises.map((ex) => (
                          <div key={ex.name} className="py-1 text-[11px]" style={{ color: "var(--color-text-secondary)" }}>{ex.name} — {ex.sets.length} sets</div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
        )}
      </div>

      {activities.length > 0 && (
        <div className="flex gap-3">
          <div className="px-3 py-2 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-secondary)", borderRadius: "3px" }}>
            <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>Sessions</span>
            <span className="text-xs font-medium ml-2" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>{activities.length}</span>
          </div>
          <div className="px-3 py-2 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-secondary)", borderRadius: "3px" }}>
            <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>Avg Duration</span>
            <span className="text-xs font-medium ml-2" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>{Math.round(activities.reduce((s, a) => s + a.duration_min, 0) / activities.length)}min</span>
          </div>
        </div>
      )}

      <button onClick={onEditBlock} className="text-[10px] font-medium px-2.5 py-1.5 border" style={{ borderColor: "var(--color-border-light)", color: "var(--color-text-muted)", borderRadius: "3px" }}>Discuss via Chat</button>
    </div>
  );
}
