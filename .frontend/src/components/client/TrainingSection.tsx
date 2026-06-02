"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import type { TrainingBlock, LiftData } from "@/lib/types";
import { formatWeight, formatDate } from "@/lib/formatters";
import { getClientLifts } from "@/lib/api";
import MetricChart from "./MetricChart";

interface TrainingSectionProps {
  training: TrainingBlock[];
  athleteId: string;
  onEditBlock: () => void;
}

export default function TrainingSection({ training, athleteId, onEditBlock }: TrainingSectionProps) {
  const [lifts, setLifts] = useState<LiftData[]>([]);
  const [flagged, setFlagged] = useState<string[]>([]);
  const [view, setView] = useState<"overview" | "explorer" | "builder" | "log">("overview");
  const [selectedExercise, setSelectedExercise] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState(28);
  const [workoutLog, setWorkoutLog] = useState<{id: string; title: string; date: string; duration_min: number; exercises: {name: string; sets: {weight_kg: number; reps: number; type: string}[]}[]}[]>([]);
  // Routine builder state
  const [routineTitle, setRoutineTitle] = useState("");
  const [routineExercises, setRoutineExercises] = useState<{name: string; sets: number; reps: number; weight: number}[]>([
    { name: "", sets: 4, reps: 10, weight: 0 },
  ]);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/coach/coach-001/client/${athleteId}/workouts?days=${timeRange}`)
      .then((r) => r.json())
      .then((d) => setWorkoutLog(d.workouts || []))
      .catch(() => {});
  }, [athleteId, timeRange]);

  useEffect(() => {
    getClientLifts("coach-001", athleteId, timeRange)
      .then((data) => { setLifts(data.lifts); setFlagged(data.flagged); })
      .catch(() => {});
  }, [athleteId, timeRange]);

  const activeBlock = training.find((t) => t.status === "active");
  const flaggedLifts = lifts.filter((l) => flagged.includes(l.exercise_template_id) || l.status !== "progressing");
  const selected = lifts.find((l) => l.exercise_template_id === selectedExercise) || lifts[0];

  // Routine builder view
  if (view === "builder") {
    return (
      <div>
        <button onClick={() => setView("overview")} className="text-xs mb-4 flex items-center gap-1" style={{ color: "var(--color-text-secondary)" }}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 11L5 7l4-4" /></svg>
          Back to overview
        </button>
        <h3 className="text-base font-semibold mb-4" style={{ fontFamily: "'Crimson Pro', serif" }}>Build Routine</h3>
        <div className="rounded-xl p-5 border space-y-4" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)" }}>
          <div>
            <label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Routine Name</label>
            <input type="text" value={routineTitle} onChange={(e) => setRoutineTitle(e.target.value)} placeholder="e.g. Push Day A" className="w-full text-sm px-3 py-2 rounded-lg border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }} />
          </div>

          <div className="space-y-3">
            <p className="text-xs font-medium" style={{ color: "var(--color-text-secondary)" }}>Exercises</p>
            {routineExercises.map((ex, i) => (
              <div key={i} className="grid grid-cols-12 gap-2 items-end">
                <div className="col-span-5">
                  {i === 0 && <label className="text-[10px] block mb-1" style={{ color: "var(--color-text-muted)" }}>Exercise</label>}
                  <input type="text" value={ex.name} onChange={(e) => { const n = [...routineExercises]; n[i].name = e.target.value; setRoutineExercises(n); }} placeholder="Bench Press" className="w-full text-xs px-2 py-1.5 rounded border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }} />
                </div>
                <div className="col-span-2">
                  {i === 0 && <label className="text-[10px] block mb-1" style={{ color: "var(--color-text-muted)" }}>Sets</label>}
                  <input type="number" value={ex.sets} onChange={(e) => { const n = [...routineExercises]; n[i].sets = +e.target.value; setRoutineExercises(n); }} className="w-full text-xs px-2 py-1.5 rounded border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace" }} />
                </div>
                <div className="col-span-2">
                  {i === 0 && <label className="text-[10px] block mb-1" style={{ color: "var(--color-text-muted)" }}>Reps</label>}
                  <input type="number" value={ex.reps} onChange={(e) => { const n = [...routineExercises]; n[i].reps = +e.target.value; setRoutineExercises(n); }} className="w-full text-xs px-2 py-1.5 rounded border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace" }} />
                </div>
                <div className="col-span-2">
                  {i === 0 && <label className="text-[10px] block mb-1" style={{ color: "var(--color-text-muted)" }}>Weight</label>}
                  <input type="number" value={ex.weight || ""} onChange={(e) => { const n = [...routineExercises]; n[i].weight = +e.target.value; setRoutineExercises(n); }} placeholder="kg" className="w-full text-xs px-2 py-1.5 rounded border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace" }} />
                </div>
                <div className="col-span-1">
                  {routineExercises.length > 1 && (
                    <button onClick={() => setRoutineExercises(routineExercises.filter((_, j) => j !== i))} className="text-xs p-1 rounded hover:opacity-70" style={{ color: "var(--color-text-muted)" }}>✕</button>
                  )}
                </div>
              </div>
            ))}
            <button onClick={() => setRoutineExercises([...routineExercises, { name: "", sets: 4, reps: 10, weight: 0 }])} className="text-xs font-medium px-3 py-1.5 rounded-lg" style={{ background: "var(--color-bg-secondary)", color: "var(--color-text-secondary)" }}>
              + Add Exercise
            </button>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              onClick={async () => {
                if (!routineTitle || !routineExercises.some((e) => e.name)) return;
                const exercises = routineExercises.filter((e) => e.name).map((e) => ({
                  title: e.name,
                  exercise_template_id: e.name.toLowerCase().replace(/\s+/g, "_"),
                  sets: Array.from({ length: e.sets }, () => ({ type: "normal", weight_kg: e.weight || undefined, reps: e.reps })),
                }));
                await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/coach/coach-001/client/${athleteId}/routine`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ title: routineTitle, exercises }),
                });
                setView("overview");
                setRoutineTitle("");
                setRoutineExercises([{ name: "", sets: 4, reps: 10, weight: 0 }]);
              }}
              disabled={!routineTitle || !routineExercises.some((e) => e.name)}
              className="text-sm font-medium px-5 py-2 rounded-lg text-white disabled:opacity-50"
              style={{ background: "var(--color-accent-primary)" }}
            >
              Push to Hevy
            </button>
            <button onClick={() => setView("overview")} className="text-sm px-4 py-2 rounded-lg" style={{ color: "var(--color-text-muted)" }}>Cancel</button>
          </div>
        </div>
      </div>
    );
  }

  // Workout log view — structured, not raw text
  if (view === "log") {
    return (
      <div>
        <button onClick={() => setView("overview")} className="text-xs mb-4 flex items-center gap-1" style={{ color: "var(--color-text-secondary)" }}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 11L5 7l4-4" /></svg>
          Back to overview
        </button>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold" style={{ fontFamily: "'Crimson Pro', serif" }}>Workout Log</h3>
          <div className="flex gap-2">
            {[14, 28, 56].map((d) => (
              <button key={d} onClick={() => setTimeRange(d)} className="text-[10px] px-2 py-1 rounded"
                style={{ background: timeRange === d ? "var(--color-accent-light)" : "var(--color-bg-secondary)", color: timeRange === d ? "var(--color-accent-primary)" : "var(--color-text-muted)" }}>
                {d === 14 ? "2wk" : d === 28 ? "4wk" : "8wk"}
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-4">
          {workoutLog.length === 0 && <p className="text-sm py-8 text-center" style={{ color: "var(--color-text-muted)" }}>No workouts logged in this period.</p>}
          {workoutLog.map((w) => (
            <div key={w.id} className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)", boxShadow: "var(--shadow-card)" }}>
              <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid var(--color-border-card)" }}>
                <div>
                  <span className="text-sm font-semibold" style={{ color: "var(--color-text-primary)" }}>{w.title}</span>
                  <span className="text-xs ml-2" style={{ color: "var(--color-text-muted)" }}>{w.date}</span>
                </div>
                <span className="text-xs" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{w.duration_min}min</span>
              </div>
              <div className="px-4 py-2">
                {w.exercises.map((ex) => (
                  <div key={ex.name} className="py-2 border-b last:border-0" style={{ borderColor: "var(--color-border-card)" }}>
                    <p className="text-xs font-medium mb-1" style={{ color: "var(--color-text-primary)" }}>{ex.name}</p>
                    <div className="flex flex-wrap gap-1.5">
                      {ex.sets.map((s, i) => (
                        <span key={i} className="text-[11px] px-2 py-0.5 rounded" style={{
                          fontFamily: "'IBM Plex Mono', monospace",
                          background: s.type === "failure" ? "var(--color-severity-concerning-bg)" : "var(--color-bg-secondary)",
                          color: s.type === "failure" ? "var(--color-severity-concerning)" : "var(--color-text-secondary)",
                        }}>
                          {formatWeight(s.weight_kg)}×{s.reps}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (view === "explorer" && lifts.length > 0) {
    return (
      <div>
        <button onClick={() => setView("overview")} className="text-xs mb-4 flex items-center gap-1" style={{ color: "var(--color-text-secondary)" }}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 11L5 7l4-4" /></svg>
          Back to overview
        </button>
        <div className="flex gap-4">
          <div className="w-48 shrink-0 space-y-1 max-h-[500px] overflow-y-auto">
            {lifts.map((l) => (
              <button key={l.exercise_template_id} onClick={() => setSelectedExercise(l.exercise_template_id)}
                className="w-full text-left px-3 py-2 rounded-lg text-xs transition-colors"
                style={{ background: selected?.exercise_template_id === l.exercise_template_id ? "var(--color-accent-light)" : "transparent", color: selected?.exercise_template_id === l.exercise_template_id ? "var(--color-accent-primary)" : "var(--color-text-secondary)" }}>
                <div className="font-medium truncate">{l.exercise_name}</div>
                <div style={{ color: "var(--color-text-muted)" }}>{l.sessions.length} sessions · {l.status === "stall" ? "⚠ Stall" : l.status === "drop" ? "↓ Drop" : "↑"}</div>
              </button>
            ))}
          </div>
          {selected && (
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-base font-semibold" style={{ fontFamily: "'Crimson Pro', serif" }}>{selected.exercise_name}</h3>
                <div className="flex gap-2">
                  {[28, 56, 84].map((d) => (
                    <button key={d} onClick={() => setTimeRange(d)} className="text-[10px] px-2 py-1 rounded"
                      style={{ background: timeRange === d ? "var(--color-accent-light)" : "var(--color-bg-secondary)", color: timeRange === d ? "var(--color-accent-primary)" : "var(--color-text-muted)" }}>
                      {d / 7}wk
                    </button>
                  ))}
                </div>
              </div>
              <MetricChart data={selected.sessions.map((s) => ({ date: s.date, value: s.working_weight_kg }))} color="var(--color-accent-primary)" height={300} unit="kg" />
              <div className="mt-4 text-xs" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
                <div className="grid grid-cols-4 gap-3 py-1.5 border-b font-medium" style={{ borderColor: "var(--color-border-card)", color: "var(--color-text-muted)" }}>
                  <span>Date</span><span>Weight</span><span>Reps</span><span>Sets</span>
                </div>
                {[...selected.sessions].reverse().map((s) => (
                  <div key={s.date} className="grid grid-cols-4 gap-3 py-1.5 border-b" style={{ borderColor: "var(--color-border-card)", color: "var(--color-text-primary)" }}>
                    <span style={{ color: "var(--color-text-muted)" }}>{s.date.slice(5)}</span>
                    <span>{formatWeight(s.working_weight_kg)}</span>
                    <span>{s.best_set_reps}</span>
                    <span>{s.set_count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {activeBlock && (
        <div className="rounded-xl p-4 border" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)", boxShadow: "var(--shadow-card)" }}>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-semibold" style={{ fontFamily: "'Crimson Pro', serif" }}>{activeBlock.name}</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full capitalize" style={{ background: "rgba(90,138,92,0.1)", color: "#5A8A5C" }}>{activeBlock.block_type}</span>
            <span className="text-[10px] ml-auto" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>Since {formatDate(activeBlock.start_date)}</span>
          </div>
          {activeBlock.notes && <p className="text-xs mt-1" style={{ color: "var(--color-text-secondary)" }}>{activeBlock.notes}</p>}
        </div>
      )}
      {flaggedLifts.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--color-text-muted)" }}>Flagged Lifts</h3>
          <div className="grid grid-cols-2 gap-3">
            {flaggedLifts.map((lift) => {
              const statusColor = lift.status === "stall" ? "#C98B2F" : lift.status === "drop" ? "#C44536" : "#5A8A5C";
              const statusLabel = lift.status === "stall" ? "Stall" : lift.status === "drop" ? "Drop" : "OK";
              const latest = lift.sessions[lift.sessions.length - 1];
              return (
                <motion.div key={lift.exercise_template_id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl p-4 border" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)", boxShadow: "var(--shadow-card)" }}>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium truncate" style={{ color: "var(--color-text-primary)" }}>{lift.exercise_name}</span>
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0" style={{ background: `${statusColor}18`, color: statusColor }}>{statusLabel}</span>
                  </div>
                  <p className="text-lg font-medium mb-2" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
                    {latest ? formatWeight(latest.working_weight_kg) : "—"}
                    {latest && <span className="text-xs ml-1" style={{ color: "var(--color-text-muted)" }}>× {latest.best_set_reps}</span>}
                  </p>
                  <MetricChart data={lift.sessions.map((s) => ({ date: s.date, value: s.working_weight_kg }))} color={statusColor} height={80} unit="kg" />
                </motion.div>
              );
            })}
          </div>
        </div>
      )}
      {lifts.length === 0 && <p className="text-sm py-4 text-center" style={{ color: "var(--color-text-muted)" }}>No workout data synced yet.</p>}
      <div className="flex flex-wrap gap-3">
        {lifts.length > 0 && (
          <button onClick={() => setView("explorer")} className="text-xs font-medium px-4 py-2 rounded-lg" style={{ background: "var(--color-bg-secondary)", color: "var(--color-text-secondary)" }}>View all exercises</button>
        )}
        {lifts.length > 0 && (
          <button onClick={() => setView("log")} className="text-xs font-medium px-4 py-2 rounded-lg" style={{ background: "var(--color-bg-secondary)", color: "var(--color-text-secondary)" }}>Workout log</button>
        )}
        <button onClick={() => setView("builder")} className="text-xs font-medium px-4 py-2 rounded-lg" style={{ background: "var(--color-accent-light)", color: "var(--color-accent-primary)" }}>Build Routine</button>
        <button onClick={onEditBlock} className="text-xs font-medium px-4 py-2 rounded-lg border" style={{ borderColor: "var(--color-border-card)", color: "var(--color-text-secondary)" }}>Edit via Chat</button>
      </div>
    </div>
  );
}
