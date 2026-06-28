"use client";

import { useEffect, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { getPatientDashboard, logSubstanceEvent } from "@/lib/api";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import type { WearableMetric, DrugLevel } from "@/lib/types";
import Chat from "@/components/Chat";
import { WEARABLE_META, getStatusStyle, formatSyncTime } from "@/lib/formatters";

const MOCK_DASHBOARD = {
  patient: { id: "patient-001", name: "Marcus Rivera", email: "marcus@example.com", avatar_color: "#E5534B", connected_at: "2026-03-01", last_sync: "2026-05-31T08:14:00Z", integrations: ["apple_health", "bloodwork"] },
  treatment_status: "active_treatment", treatment_days: 28,
  wearables: [
    { metric: "resting_hr", observation_date: "2026-05-31", value_mean: 58, unit: "bpm", source: "apple_health" },
    { metric: "hrv", observation_date: "2026-05-31", value_mean: 42, unit: "ms", source: "apple_health" },
    { metric: "weight", observation_date: "2026-05-31", value_mean: 98.2, unit: "kg", source: "apple_health" },
    { metric: "recovery_score", observation_date: "2026-05-31", value_mean: 68, unit: "%", source: "apple_health" },
  ],
  drug_levels: [
    { compound_name: "Testosterone Enanthate", compound_class: "anabolic", level: 0.82, dose_active_mg: 500, at_steady_state: true, observation_date: "2026-05-31" },
    { compound_name: "Anavar", compound_class: "anabolic", level: 0.95, dose_active_mg: 50, at_steady_state: true, observation_date: "2026-05-31" },
  ],
  training: [] as { id: string; name: string; start_date: string; notes: string | null; status: string }[],
  nutrition: [] as { calories: number; protein_g: number; carbs_g: number; fat_g: number; notes: string | null; effective_date: string }[],
  recovery: [] as { id: string; note_type: string; content: string; created_at: string }[],
};

export default function PatientDashboard() {
  const [dashboard, setDashboard] = useState<typeof MOCK_DASHBOARD | null>(null);
  const [loading, setLoading] = useState(true);
  const [showLogForm, setShowLogForm] = useState(false);
  const [logType, setLogType] = useState("START");
  const [logCompound, setLogCompound] = useState("");
  const [logClass, setLogClass] = useState("anabolic");
  const [logDose, setLogDose] = useState("");
  const [logFrequency, setLogFrequency] = useState("");
  const [logRoute, setLogRoute] = useState("IM");
  const [submitting, setSubmitting] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [notifications, setNotifications] = useState<{ id: number; type: string; title: string; body: string | null }[]>([]);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/patient/patient-001/notifications`)
      .then((r) => r.json()).then((d) => setNotifications(d.notifications?.filter((n: { read: number }) => !n.read) || [])).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    getPatientDashboard("patient-001")
      .then((data: Record<string, unknown>) => {
        if (cancelled) return;
        const raw = data as typeof MOCK_DASHBOARD & { integrations?: { provider: string }[] };
        if (raw.integrations && !raw.patient.integrations) raw.patient.integrations = raw.integrations.map((i: { provider: string }) => i.provider);
        if (!raw.patient.integrations) raw.patient.integrations = [];
        if (!raw.patient.last_sync) (raw.patient as { last_sync: string | null }).last_sync = null;
        setDashboard(raw);
        setLoading(false);
      })
      .catch(() => { if (!cancelled) { setDashboard(MOCK_DASHBOARD); setLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  const handleLogSubmit = async () => {
    if (!logCompound) return;
    setSubmitting(true);
    try { await logSubstanceEvent("patient-001", { compound_name: logCompound, compound_class: logClass, event_type: logType, dose_mg: logDose ? parseFloat(logDose) : undefined, frequency: logFrequency || undefined, route: logRoute || undefined }); } catch {}
    setSubmitting(false); setShowLogForm(false); setLogCompound(""); setLogDose(""); setLogFrequency("");
  };

  if (loading || !dashboard) {
    return (
      <div className="min-h-screen" style={{ background: "var(--color-bg-primary)" }}>
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="h-6 w-40 animate-shimmer mb-2" style={{ background: "var(--color-bg-secondary)" }} />
          <div className="h-4 w-56 animate-shimmer mb-6" style={{ background: "var(--color-bg-secondary)" }} />
          <div className="grid grid-cols-4 gap-3">{[0, 1, 2, 3].map((i) => <div key={i} className="h-20 animate-shimmer" style={{ background: "var(--color-bg-secondary)" }} />)}</div>
        </div>
      </div>
    );
  }

  const ss = getStatusStyle(dashboard.treatment_status);

  return (
    <div className="min-h-screen" style={{ background: "var(--color-bg-primary)" }}>
      {/* Header */}
      <header className="sticky top-0 z-20 border-b" style={{ background: "var(--color-bg-secondary)", borderColor: "var(--color-border-light)" }}>
        <div className="max-w-4xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <a href="/" className="text-sm font-semibold" style={{ color: "var(--color-text-primary)" }}>Clinic Platform</a>
            <span className="text-[9px] font-medium px-1.5 py-0.5 uppercase" style={{ background: "var(--color-success-bg)", color: "var(--color-success)", borderRadius: "2px" }}>Patient</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{dashboard.patient.name}</span>
            <div className="w-6 h-6 rounded flex items-center justify-center text-[9px] font-medium" style={{ background: `${dashboard.patient.avatar_color}18`, color: dashboard.patient.avatar_color }}>
              {dashboard.patient.name.split(" ").map((n) => n[0]).join("")}
            </div>
          </div>
        </div>
      </header>

      {/* Notification queue */}
      <div className="max-w-4xl mx-auto px-6 pt-4">
        <div className="border overflow-hidden" style={{ borderColor: notifications.length > 0 ? "var(--color-accent-primary)" : "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
          <div className="px-3 py-2 flex items-center justify-between" style={{ background: notifications.length > 0 ? "var(--color-accent-light)" : "var(--color-bg-secondary)", borderBottom: `1px solid ${notifications.length > 0 ? "rgba(76,141,255,0.2)" : "var(--color-border-light)"}` }}>
            <div className="flex items-center gap-1.5">
              {notifications.length > 0 ? (
                <>
                  <span className="w-2 h-2 rounded-full" style={{ background: "var(--color-accent-primary)" }} />
                  <span className="text-xs font-medium" style={{ color: "var(--color-accent-primary)" }}>{notifications.length} update{notifications.length !== 1 ? "s" : ""} from your clinician</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full" style={{ background: "var(--color-success)" }} />
                  <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>All caught up — no new messages</span>
                </>
              )}
            </div>
            {notifications.length > 0 && (
              <button onClick={async () => {
                await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/patient/patient-001/notifications/read`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ notification_ids: null }) });
                setNotifications([]);
              }} className="text-[10px] font-medium px-2.5 py-1 text-white" style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}>Acknowledge all</button>
            )}
          </div>
          {notifications.length > 0 && (
            <div className="max-h-[200px] overflow-y-auto">
              {notifications.map((n) => (
                <div key={n.id} className="px-3 py-2 border-b" style={{ borderColor: "var(--color-border-light)" }}>
                  <p className="text-xs" style={{ color: "var(--color-text-primary)" }}>{n.title}</p>
                  {n.body && <p className="text-[10px] mt-0.5 truncate" style={{ color: "var(--color-text-muted)" }}>{n.body}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <main className="max-w-4xl mx-auto px-6 py-6">
        {/* Title */}
        <div className="mb-5">
          <h1 className="text-lg font-semibold">Your Dashboard</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[9px] font-medium px-1.5 py-0.5 capitalize" style={{ background: ss.bg, color: ss.text, borderRadius: "2px" }}>{dashboard.treatment_status.replace(/_/g, " ")}{dashboard.treatment_days ? ` · ${dashboard.treatment_days}d` : ""}</span>
            <span className="text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>
              {dashboard.patient.last_sync ? formatSyncTime(dashboard.patient.last_sync) : "Not synced"}
            </span>
          </div>
        </div>

        {/* Upload buttons */}
        <div className="flex items-center gap-2 mb-3">
          <label className="inline-flex items-center gap-1.5 text-[10px] font-medium px-2.5 py-1.5 border cursor-pointer" style={{ borderColor: "var(--color-accent-primary)", color: "var(--color-accent-primary)", background: "var(--color-accent-light)", borderRadius: "3px" }}>
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M5 1v8M1 5h8" /></svg>
            Upload Bloodwork
            <input type="file" accept=".pdf,.png,.jpg,.jpeg,.heic" className="hidden" onChange={async (e) => {
              const file = e.target.files?.[0]; if (!file) return;
              const form = new FormData(); form.append("file", file);
              try { const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/patient/patient-001/upload`, { method: "POST", body: form }); const data = await res.json(); alert(data.status === "success" ? `${data.results_count} results, ${data.findings_count} findings` : `Error: ${data.reason || "Failed"}`); } catch { alert("Upload failed"); }
            }} />
          </label>
          <label className="inline-flex items-center gap-1.5 text-[10px] font-medium px-2.5 py-1.5 border cursor-pointer" style={{ borderColor: "var(--color-border-light)", color: "var(--color-text-secondary)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M8 6v3H2V6M5 1v5M3 3l2-2 2 2" /></svg>
            Import Apple Health
            <input type="file" accept=".zip,.xml" className="hidden" onChange={async (e) => {
              const file = e.target.files?.[0]; if (!file) return;
              const form = new FormData(); form.append("file", file);
              try { const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/patient/patient-001/import/apple-health`, { method: "POST", body: form }); const data = await res.json(); alert(data.status === "success" ? `${data.records} records, ${data.findings_count} findings` : `Error: ${data.reason || "Failed"}`); } catch { alert("Import failed"); }
            }} />
          </label>
        </div>

        {/* Integrations */}
        <div className="flex items-center gap-2 mb-6">
          {dashboard.patient.integrations.map((intg) => (
            <span key={intg} className="inline-flex items-center gap-1 text-[10px] px-2 py-1 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", color: "var(--color-text-secondary)", borderRadius: "3px" }}>
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--color-success)" }} />
              {intg.replace("_", " ")}
            </span>
          ))}
        </div>

        {/* Wearables */}
        <div className="mb-6">
          <h2 className="text-sm font-semibold mb-2">Wearable Trends</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            {(() => {
              const byMetric: Record<string, { latest: WearableMetric; history: { v: number }[] }> = {};
              const sorted = [...dashboard.wearables].sort((a, b) => a.observation_date.localeCompare(b.observation_date));
              sorted.forEach((w: WearableMetric) => {
                if (!byMetric[w.metric]) byMetric[w.metric] = { latest: w, history: [] };
                byMetric[w.metric].history.push({ v: w.value_mean });
                if (w.observation_date >= byMetric[w.metric].latest.observation_date) byMetric[w.metric].latest = w;
              });
              return Object.entries(byMetric)
                .sort(([a], [b]) => (WEARABLE_META[a]?.priority || 99) - (WEARABLE_META[b]?.priority || 99))
                .map(([metric, { latest, history }]) => {
                  const meta = WEARABLE_META[metric] || { label: metric, color: "#565B6E", priority: 99 };
                  return (
                    <div key={metric} className="border p-3" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
                      <p className="text-[10px] font-medium uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>{meta.label}</p>
                      <p className="text-base font-medium mt-0.5" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>{latest.value_mean} <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>{latest.unit}</span></p>
                      <div className="mt-1.5" style={{ height: 32 }}>
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={history}><Line type="monotone" dataKey="v" stroke={meta.color} strokeWidth={1.5} dot={false} /></LineChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  );
                });
            })()}
          </div>
        </div>

        {/* Stack */}
        <div className="mb-6">
          <h2 className="text-sm font-semibold mb-2">My Stack</h2>
          <div className="border p-4" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
            <div className="space-y-3">
              {(() => {
                const latestDate = dashboard.drug_levels.length > 0 ? dashboard.drug_levels.reduce((max: string, dl: DrugLevel) => dl.observation_date > max ? dl.observation_date : max, dashboard.drug_levels[0].observation_date) : "";
                return dashboard.drug_levels.filter((dl: DrugLevel) => dl.observation_date === latestDate);
              })().map((dl: DrugLevel) => (
                <div key={dl.compound_name}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-medium">{dl.compound_name}</span>
                      <span className="text-[9px] px-1 py-0.5" style={{ fontFamily: "'IBM Plex Mono', monospace", background: "var(--color-bg-hover)", color: "var(--color-text-muted)", borderRadius: "2px" }}>{dl.dose_active_mg}mg</span>
                    </div>
                    <span className="text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{Math.round(dl.level * 100)}%{dl.at_steady_state ? " steady" : ""}</span>
                  </div>
                  <div className="h-1.5 overflow-hidden" style={{ background: "var(--color-border-light)", borderRadius: "1px" }}>
                    <div className="h-full" style={{ width: `${dl.level * 100}%`, background: "var(--color-accent-primary)", borderRadius: "1px" }} />
                  </div>
                </div>
              ))}
            </div>
            <p className="text-[10px] mt-3" style={{ color: "var(--color-text-muted)" }}>Estimated from logged protocol</p>
          </div>
        </div>

        {/* Clinician care plan */}
        {(dashboard.training?.length > 0 || dashboard.nutrition?.length > 0 || dashboard.recovery?.length > 0) && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold mb-2">Your Care Plan <span className="text-[10px] font-normal" style={{ color: "var(--color-text-muted)" }}>Set by your clinician</span></h2>
            <div className="space-y-2">
              {dashboard.training?.filter((t: { status: string }) => t.status === "active").map((block: { id: string; name: string; start_date: string; notes: string | null }) => (
                <div key={block.id} className="border p-3" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="text-xs font-medium">{block.name}</span>
                    <span className="text-[9px] font-medium px-1.5 py-0.5" style={{ background: "var(--color-success-bg)", color: "var(--color-success)", borderRadius: "2px" }}>Active</span>
                  </div>
                  {block.notes && <p className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>{block.notes}</p>}
                </div>
              ))}
              {dashboard.nutrition?.length > 0 && (() => {
                const n = dashboard.nutrition[0] as { calories: number; protein_g: number; carbs_g: number; fat_g: number; notes: string | null; effective_date: string };
                return (
                  <div className="border p-3" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
                    <div className="flex items-baseline gap-1.5 mb-1">
                      <span className="text-base font-medium" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>{n.calories}</span>
                      <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>kcal/day</span>
                      <span className="text-[10px] ml-auto" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>Since {new Date(n.effective_date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
                    </div>
                    <div className="flex gap-3 text-[11px]" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
                      <span style={{ color: "#E5534B" }}>{n.protein_g}g pro</span>
                      <span style={{ color: "#D4952A" }}>{n.carbs_g}g carb</span>
                      <span style={{ color: "#4C8DFF" }}>{n.fat_g}g fat</span>
                    </div>
                    {n.notes && <p className="text-[11px] mt-1" style={{ color: "var(--color-text-secondary)" }}>{n.notes}</p>}
                  </div>
                );
              })()}
              {dashboard.recovery?.slice(0, 3).map((note: { id: string; note_type: string; content: string; created_at: string }) => (
                <div key={note.id} className="border p-2.5" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="text-[9px] font-medium px-1 py-0.5 uppercase" style={{ background: "var(--color-accent-light)", color: "var(--color-accent-primary)", borderRadius: "2px" }}>{note.note_type.replace(/_/g, " ")}</span>
                    <span className="text-[9px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{new Date(note.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{note.content}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Log */}
        <div className="mb-8">
          <h2 className="text-sm font-semibold mb-2">Log Entry</h2>
          <div className="flex gap-2 mb-3">
            {(["START", "STOP", "DOSE_CHANGE"] as const).map((type) => (
              <button key={type} onClick={() => { setLogType(type); setShowLogForm(true); }} className="text-xs font-medium px-3 py-1.5 border" style={{ borderColor: logType === type && showLogForm ? "var(--color-accent-primary)" : "var(--color-border-light)", background: logType === type && showLogForm ? "var(--color-accent-light)" : "var(--color-bg-card)", color: logType === type && showLogForm ? "var(--color-accent-primary)" : "var(--color-text-secondary)", borderRadius: "3px" }}>
                {type === "START" ? "Start Compound" : type === "STOP" ? "Stop Compound" : "Dose Change"}
              </button>
            ))}
          </div>
          {showLogForm && (
            <div className="border p-3 space-y-2" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
              <div className="grid grid-cols-2 gap-2">
                <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Compound</label><input type="text" value={logCompound} onChange={(e) => setLogCompound(e.target.value)} placeholder="Testosterone Enanthate" className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }} /></div>
                <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Class</label><select value={logClass} onChange={(e) => setLogClass(e.target.value)} className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }}><option value="anabolic">Anabolic</option><option value="ancillary">Ancillary</option><option value="peptide">Peptide</option><option value="sarm">SARM</option><option value="prescription">Prescription</option></select></div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Dose (mg)</label><input type="number" value={logDose} onChange={(e) => setLogDose(e.target.value)} placeholder="500" className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-primary)", borderRadius: "3px" }} /></div>
                <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Frequency</label><input type="text" value={logFrequency} onChange={(e) => setLogFrequency(e.target.value)} placeholder="2x/week" className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }} /></div>
                <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Route</label><select value={logRoute} onChange={(e) => setLogRoute(e.target.value)} className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }}><option value="IM">IM</option><option value="subQ">SubQ</option><option value="oral">Oral</option><option value="transdermal">Transdermal</option></select></div>
              </div>
              <div className="flex gap-2">
                <button onClick={handleLogSubmit} disabled={submitting || !logCompound} className="text-xs font-medium px-3 py-1.5 text-white disabled:opacity-30" style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}>{submitting ? "Logging..." : `Log ${logType.replace("_", " ")}`}</button>
                <button onClick={() => setShowLogForm(false)} className="text-xs px-2 py-1.5" style={{ color: "var(--color-text-muted)" }}>Cancel</button>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Chat FAB */}
      {!showChat && (
        <button onClick={() => setShowChat(true)} className="fixed bottom-4 right-4 w-10 h-10 rounded flex items-center justify-center z-40" style={{ background: "var(--color-accent-primary)" }}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="white" strokeWidth="1.5" strokeLinecap="round"><path d="M15.75 11.25a1.5 1.5 0 0 1-1.5 1.5H5.25l-3 3V3.75a1.5 1.5 0 0 1 1.5-1.5h10.5a1.5 1.5 0 0 1 1.5 1.5z" /></svg>
        </button>
      )}

      <AnimatePresence>{showChat && <Chat role="patient" patientId="patient-001" onClose={() => setShowChat(false)} />}</AnimatePresence>
    </div>
  );
}
