"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { getAthleteDashboard, logSubstanceEvent } from "@/lib/api";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import type { Finding, WearableMetric, DrugLevel } from "@/lib/types";
import Chat from "@/components/Chat";

/* ── Mock data ── */
const MOCK_DASHBOARD = {
  athlete: { id: "athlete-001", name: "Marcus Rivera", email: "marcus@example.com", avatar_color: "#C44536", connected_at: "2026-03-01", last_sync: "2026-05-31T08:14:00Z", integrations: ["apple_health", "bloodwork"] },
  phase: "blast",
  day_in_phase: 28,
  findings: [
    { id: "f1", detector_id: "lipid_shift", theme: "Lipid Panel", severity: "concerning" as const, headline: "LDL surged 42% over 6 weeks", summary: "LDL cholesterol rose from 112 to 159 mg/dL.", signals: [{ label: "LDL", value: "159 mg/dL", direction: "up" as const, delta: "+42%" }], detected_at: "2026-05-30", status: "active" as const },
  ],
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
};

// Import shared WEARABLE_META with priority values
import { WEARABLE_META } from "@/lib/formatters";

function generateSparkline(base: number, variance: number): { v: number }[] {
  return Array.from({ length: 14 }, (_, i) => ({
    v: base + (Math.sin(i * 0.8) * variance) + (Math.random() - 0.5) * variance * 0.5,
  }));
}

function getSeverityColor(severity: Finding["severity"]): string {
  switch (severity) {
    case "concerning": return "#C44536";
    case "notable": return "#C98B2F";
    case "info": return "#4A7FA5";
  }
}

function getSeverityBg(severity: Finding["severity"]): string {
  switch (severity) {
    case "concerning": return "var(--color-severity-concerning-bg)";
    case "notable": return "var(--color-severity-notable-bg)";
    case "info": return "var(--color-severity-info-bg)";
  }
}

function getPhaseStyle(phase: string): { bg: string; text: string } {
  switch (phase) {
    case "blast": return { bg: "rgba(196, 69, 54, 0.1)", text: "#C44536" };
    case "cruise": return { bg: "rgba(74, 127, 165, 0.1)", text: "#4A7FA5" };
    case "prep": return { bg: "rgba(123, 104, 174, 0.1)", text: "#7B68AE" };
    case "offseason": return { bg: "rgba(90, 138, 92, 0.1)", text: "#5A8A5C" };
    default: return { bg: "rgba(155, 148, 141, 0.1)", text: "#9B948D" };
  }
}

function formatDate(d: string): string {
  return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatSyncTime(sync: string | null): string {
  if (!sync) return "Never synced";
  const d = new Date(sync);
  const now = new Date();
  const diffH = Math.floor((now.getTime() - d.getTime()) / 3600000);
  if (diffH < 1) return "Just now";
  if (diffH < 24) return `${diffH}h ago`;
  return `${Math.floor(diffH / 24)}d ago`;
}

export default function AthleteDashboard() {
  const [dashboard, setDashboard] = useState<typeof MOCK_DASHBOARD | null>(null);
  const [loading, setLoading] = useState(true);
  const [showLogForm, setShowLogForm] = useState(false);
  const [logType, setLogType] = useState<string>("START");
  const [logCompound, setLogCompound] = useState("");
  const [logClass, setLogClass] = useState("anabolic");
  const [logDose, setLogDose] = useState("");
  const [logFrequency, setLogFrequency] = useState("");
  const [logRoute, setLogRoute] = useState("IM");
  const [submitting, setSubmitting] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [notifications, setNotifications] = useState<{ id: number; type: string; title: string; body: string | null }[]>([]);

  // Fetch unread notifications
  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/athlete/athlete-001/notifications`)
      .then((r) => r.json())
      .then((d) => setNotifications(d.notifications?.filter((n: { read: number }) => !n.read) || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    getAthleteDashboard("athlete-001")
      .then((data: Record<string, unknown>) => {
        if (cancelled) return;
        // Normalize API response — integrations may be objects or strings
        const raw = data as typeof MOCK_DASHBOARD & { integrations?: { provider: string }[] };
        if (raw.integrations && !raw.athlete.integrations) {
          raw.athlete.integrations = raw.integrations.map((i: { provider: string }) => i.provider);
        }
        if (!raw.athlete.integrations) raw.athlete.integrations = [];
        if (!raw.athlete.last_sync) raw.athlete.last_sync = null;
        setDashboard(raw);
        setLoading(false);
      })
      .catch(() => { if (!cancelled) { setDashboard(MOCK_DASHBOARD); setLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  const handleLogSubmit = async () => {
    if (!logCompound) return;
    setSubmitting(true);
    try {
      await logSubstanceEvent("athlete-001", {
        compound_name: logCompound,
        compound_class: logClass,
        event_type: logType,
        dose_mg: logDose ? parseFloat(logDose) : undefined,
        frequency: logFrequency || undefined,
        route: logRoute || undefined,
      });
    } catch {
      // Demo mode — silently succeed
    }
    setSubmitting(false);
    setShowLogForm(false);
    setLogCompound("");
    setLogDose("");
    setLogFrequency("");
  };

  if (loading || !dashboard) {
    return (
      <div className="min-h-screen" style={{ background: "var(--color-bg-primary)" }}>
        <div className="max-w-5xl mx-auto px-8 py-10">
          <div className="h-8 w-48 rounded animate-shimmer mb-2" style={{ background: "var(--color-bg-secondary)" }} />
          <div className="h-4 w-64 rounded animate-shimmer mb-8" style={{ background: "var(--color-bg-secondary)" }} />
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="h-28 rounded-xl animate-shimmer" style={{ background: "var(--color-bg-secondary)" }} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const ps = getPhaseStyle(dashboard.phase);

  return (
    <div className="min-h-screen" style={{ background: "var(--color-bg-primary)" }}>
      {/* Top Header Bar */}
      <header
        className="sticky top-0 z-20 border-b"
        style={{ background: "var(--color-bg-card)", borderColor: "var(--color-border-card)", boxShadow: "var(--shadow-card)" }}
      >
        <div className="max-w-5xl mx-auto px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <a href="/" className="text-lg font-semibold" style={{ fontFamily: "'Crimson Pro', serif", color: "var(--color-text-primary)" }}>
              Coach Platform
            </a>
            <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "rgba(90,138,92,0.1)", color: "#5A8A5C" }}>
              Athlete View
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{dashboard.athlete.name}</span>
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium"
              style={{ background: `${dashboard.athlete.avatar_color}18`, color: dashboard.athlete.avatar_color }}
            >
              {dashboard.athlete.name.split(" ").map((n) => n[0]).join("")}
            </div>
          </div>
        </div>
      </header>

      {/* Message queue — always visible */}
      <div className="max-w-5xl mx-auto px-8 pt-4">
        <div
          className="rounded-xl overflow-hidden"
          style={{ border: notifications.length > 0 ? "1px solid var(--color-accent-primary)" : "1px solid var(--color-border-card)", background: "var(--color-bg-card)" }}
        >
          <div className="px-4 py-3 flex items-center justify-between" style={{ background: notifications.length > 0 ? "var(--color-accent-light)" : "var(--color-bg-secondary)", borderBottom: `1px solid ${notifications.length > 0 ? "var(--color-accent-primary)" : "var(--color-border-card)"}` }}>
            <div className="flex items-center gap-2">
              {notifications.length > 0 ? (
                <>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--color-accent-primary)" strokeWidth="1.5" strokeLinecap="round">
                    <circle cx="8" cy="8" r="6" /><path d="M8 5v3.5M8 10.5h.01" />
                  </svg>
                  <span className="text-sm font-semibold" style={{ color: "var(--color-accent-primary)" }}>
                    {notifications.length} update{notifications.length !== 1 ? "s" : ""} from your coach
                  </span>
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="var(--color-success)" strokeWidth="1.5" strokeLinecap="round">
                    <circle cx="8" cy="8" r="6" /><path d="M5.5 8l2 2 3-3.5" />
                  </svg>
                  <span className="text-sm" style={{ color: "var(--color-text-muted)" }}>All caught up — no new messages</span>
                </>
              )}
            </div>
            {notifications.length > 0 && (
              <button
                onClick={async () => {
                  await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/athlete/athlete-001/notifications/read`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ notification_ids: null }),
                  });
                  setNotifications([]);
                }}
                className="text-xs font-medium px-4 py-1.5 rounded-lg"
                style={{ background: "var(--color-accent-primary)", color: "white" }}
              >
                Acknowledge all
              </button>
            )}
          </div>
          {notifications.length > 0 && (
            <div className="max-h-[240px] overflow-y-auto divide-y" style={{ borderColor: "var(--color-border-card)" }}>
              {notifications.map((n) => (
                <div key={n.id} className="px-4 py-2.5 flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm" style={{ color: "var(--color-text-primary)" }}>{n.title}</p>
                    {n.body && <p className="text-xs mt-0.5 truncate" style={{ color: "var(--color-text-muted)" }}>{n.body}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-8 py-8">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <h1 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: "'Crimson Pro', serif" }}>
            Your Dashboard
          </h1>
          <div className="flex items-center gap-3 mt-2">
            <span
              className="text-xs font-medium px-2.5 py-1 rounded-full capitalize"
              style={{ background: ps.bg, color: ps.text }}
            >
              {dashboard.phase} · Day {dashboard.day_in_phase}
            </span>
            <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
              {dashboard.athlete.last_sync ? `Synced ${formatSyncTime(dashboard.athlete.last_sync)}` : "Not yet synced"}
            </span>
          </div>
        </motion.div>

        {/* Data Import */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.03 }} className="mt-6">
          <div className="flex items-center gap-3 flex-wrap">
            <label
              className="inline-flex items-center gap-2 text-xs font-medium px-4 py-2 rounded-lg border cursor-pointer hover:opacity-80 transition-opacity"
              style={{ borderColor: "var(--color-accent-primary)", color: "var(--color-accent-primary)", background: "var(--color-accent-light)" }}
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M7 1v12M1 7h12" />
              </svg>
              Upload Bloodwork
              <input type="file" accept=".pdf,.png,.jpg,.jpeg,.heic" className="hidden" onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                const form = new FormData();
                form.append("file", file);
                try {
                  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/athlete/athlete-001/upload`, { method: "POST", body: form });
                  const data = await res.json();
                  alert(data.status === "success" ? `Uploaded: ${data.results_count} results, ${data.findings_count} findings` : `Error: ${data.reason || "Upload failed"}`);
                } catch { alert("Upload failed"); }
              }} />
            </label>
            <label
              className="inline-flex items-center gap-2 text-xs font-medium px-4 py-2 rounded-lg border cursor-pointer hover:opacity-80 transition-opacity"
              style={{ borderColor: "var(--color-border-card)", color: "var(--color-text-secondary)", background: "var(--color-bg-card)" }}
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 8v4a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V8M7 1v8M4 4l3-3 3 3" />
              </svg>
              Import Apple Health
              <input type="file" accept=".zip,.xml" className="hidden" onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                const form = new FormData();
                form.append("file", file);
                try {
                  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/athlete/athlete-001/import/apple-health`, { method: "POST", body: form });
                  const data = await res.json();
                  alert(data.status === "success" ? `Imported: ${data.records} records, ${data.findings_count} findings` : `Error: ${data.reason || "Import failed"}`);
                } catch { alert("Import failed"); }
              }} />
            </label>
          </div>
        </motion.div>

        {/* Sync Status */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="mt-4">
          <div className="flex items-center gap-3 flex-wrap">
            {dashboard.athlete.integrations.map((intg) => (
              <span
                key={intg}
                className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border"
                style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)", color: "var(--color-text-secondary)" }}
              >
                <span className="w-2 h-2 rounded-full" style={{ background: "var(--color-success)" }} />
                {intg.replace("_", " ")}
              </span>
            ))}
          </div>
        </motion.div>

        {/* Active Findings */}
        {dashboard.findings.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mt-8">
            <h2 className="text-xl font-semibold mb-4" style={{ fontFamily: "'Crimson Pro', serif" }}>Active Findings</h2>
            <div className="space-y-3">
              {dashboard.findings.map((f: Finding) => (
                <div
                  key={f.id}
                  className="rounded-xl border-l-[3px] p-4 border"
                  style={{
                    borderLeftColor: getSeverityColor(f.severity),
                    borderColor: "var(--color-border-card)",
                    borderLeftWidth: "3px",
                    background: getSeverityBg(f.severity),
                  }}
                >
                  <p className="text-xs font-medium uppercase tracking-wider" style={{ color: getSeverityColor(f.severity) }}>
                    {f.theme} · {f.severity}
                  </p>
                  <p className="text-sm font-medium mt-1">{f.headline}</p>
                  <p className="text-xs mt-1.5" style={{ color: "var(--color-text-secondary)" }}>{f.summary}</p>
                  <div className="flex flex-wrap gap-2 mt-3">
                    {f.signals.map((sig) => {
                      const dirColor = sig.direction === "up" ? "#C44536" : sig.direction === "down" ? "#4A7FA5" : "var(--color-text-muted)";
                      const arrow = sig.direction === "up" ? "↑" : sig.direction === "down" ? "↓" : "→";
                      return (
                        <div
                          key={sig.label}
                          className="px-3 py-2 rounded-lg"
                          style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border-card)" }}
                        >
                          <div className="text-[10px] font-medium uppercase tracking-wide mb-0.5" style={{ color: "var(--color-text-muted)" }}>{sig.label}</div>
                          <div className="flex items-baseline gap-1.5">
                            <span className="text-sm font-semibold" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-primary)" }}>{sig.value}</span>
                            <span className="text-xs font-bold" style={{ color: dirColor }}>{arrow}</span>
                            {sig.delta && <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>{sig.delta}</span>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Wearable Trends */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="mt-8">
          <h2 className="text-xl font-semibold mb-4" style={{ fontFamily: "'Crimson Pro', serif" }}>Wearable Trends</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {(() => {
              // Group wearables by metric
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
                const meta = WEARABLE_META[metric] || { label: metric, color: "#9B948D", priority: 99 };
                return (
                  <div
                    key={metric}
                    className="rounded-xl p-4 border"
                    style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)", boxShadow: "var(--shadow-card)" }}
                  >
                    <p className="text-xs font-medium" style={{ color: "var(--color-text-muted)" }}>{meta.label}</p>
                    <p className="text-xl font-medium mt-1" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
                      {latest.value_mean} <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>{latest.unit}</span>
                    </p>
                    <div className="mt-2" style={{ height: 40 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={history}>
                          <Line type="monotone" dataKey="v" stroke={meta.color} strokeWidth={1.5} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                );
              });
            })()}
          </div>
        </motion.div>

        {/* My Stack */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="mt-8">
          <h2 className="text-xl font-semibold mb-4" style={{ fontFamily: "'Crimson Pro', serif" }}>My Stack</h2>
          <div
            className="rounded-xl p-5 border"
            style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)", boxShadow: "var(--shadow-card)" }}
          >
            <div className="space-y-4">
              {(() => {
                // Show only latest date per compound
                const latestDate = dashboard.drug_levels.length > 0
                  ? dashboard.drug_levels.reduce((max: string, dl: DrugLevel) => dl.observation_date > max ? dl.observation_date : max, dashboard.drug_levels[0].observation_date)
                  : "";
                return dashboard.drug_levels.filter((dl: DrugLevel) => dl.observation_date === latestDate);
              })().map((dl: DrugLevel) => (
                <div key={dl.compound_name}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{dl.compound_name}</span>
                      <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(0,0,0,0.04)", color: "var(--color-text-muted)" }}>
                        {dl.dose_active_mg}mg
                      </span>
                    </div>
                    <span className="text-xs" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>
                      {Math.round(dl.level * 100)}%{dl.at_steady_state ? " steady" : ""}
                    </span>
                  </div>
                  <div className="h-2.5 rounded-full overflow-hidden" style={{ background: "var(--color-border-light)" }}>
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${dl.level * 100}%` }}
                      transition={{ duration: 0.8, delay: 0.3 }}
                      className="h-full rounded-full"
                      style={{ background: "var(--color-accent-primary)" }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs mt-4" style={{ color: "var(--color-text-muted)" }}>Estimated from logged protocol</p>
          </div>
        </motion.div>

        {/* Coach Programming (visible to athlete) */}
        {(dashboard.training?.length > 0 || dashboard.nutrition?.length > 0 || dashboard.recovery?.length > 0) && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.22 }} className="mt-8">
            <h2 className="text-xl font-semibold mb-4" style={{ fontFamily: "'Crimson Pro', serif" }}>
              Your Programming
              <span className="text-xs font-normal ml-2" style={{ color: "var(--color-text-muted)" }}>Set by your coach</span>
            </h2>
            <div className="space-y-4">
              {/* Training */}
              {dashboard.training?.filter((t: { status: string }) => t.status === "active").map((block: { id: string; name: string; block_type: string; start_date: string; notes: string | null }) => (
                <div key={block.id} className="rounded-xl p-4 border" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)", boxShadow: "var(--shadow-card)" }}>
                  <div className="flex items-center gap-2 mb-1">
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--color-accent-primary)" strokeWidth="1.5" strokeLinecap="round"><circle cx="7" cy="7" r="5" /><path d="M7 4v3l2 1" /></svg>
                    <span className="text-sm font-medium">{block.name}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full capitalize" style={{ background: "rgba(90,138,92,0.1)", color: "#5A8A5C" }}>{block.block_type}</span>
                  </div>
                  {block.notes && <p className="text-xs mt-1" style={{ color: "var(--color-text-secondary)" }}>{block.notes}</p>}
                </div>
              ))}
              {/* Nutrition */}
              {dashboard.nutrition?.length > 0 && (() => {
                const n = dashboard.nutrition[0] as { calories: number; protein_g: number; carbs_g: number; fat_g: number; notes: string | null; effective_date: string };
                return (
                  <div className="rounded-xl p-4 border" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)", boxShadow: "var(--shadow-card)" }}>
                    <div className="flex items-baseline gap-2 mb-2">
                      <span className="text-lg font-medium" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>{n.calories}</span>
                      <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>kcal/day</span>
                      <span className="text-xs ml-auto" style={{ color: "var(--color-text-muted)" }}>Since {new Date(n.effective_date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
                    </div>
                    <div className="flex gap-4 text-xs" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
                      <span style={{ color: "#C44536" }}>{n.protein_g}g pro</span>
                      <span style={{ color: "#C98B2F" }}>{n.carbs_g}g carb</span>
                      <span style={{ color: "#4A7FA5" }}>{n.fat_g}g fat</span>
                    </div>
                    {n.notes && <p className="text-xs mt-2" style={{ color: "var(--color-text-secondary)" }}>{n.notes}</p>}
                  </div>
                );
              })()}
              {/* Recovery Notes */}
              {dashboard.recovery?.slice(0, 3).map((note: { id: string; note_type: string; content: string; created_at: string }) => (
                <div key={note.id} className="rounded-xl p-3 border" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)" }}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium px-2 py-0.5 rounded capitalize" style={{ background: "var(--color-accent-light)", color: "var(--color-accent-primary)" }}>{note.note_type.replace(/_/g, " ")}</span>
                    <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>{new Date(note.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>{note.content}</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Log Entry */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }} className="mt-8 mb-12">
          <h2 className="text-xl font-semibold mb-4" style={{ fontFamily: "'Crimson Pro', serif" }}>Log Entry</h2>

          <div className="flex gap-3 mb-4">
            {(["START", "STOP", "DOSE_CHANGE"] as const).map((type) => (
              <button
                key={type}
                onClick={() => { setLogType(type); setShowLogForm(true); }}
                className="text-sm font-medium px-4 py-2 rounded-lg border transition-all"
                style={{
                  borderColor: logType === type && showLogForm ? "var(--color-accent-primary)" : "var(--color-border-card)",
                  background: logType === type && showLogForm ? "var(--color-accent-light)" : "var(--color-bg-card)",
                  color: logType === type && showLogForm ? "var(--color-accent-primary)" : "var(--color-text-secondary)",
                }}
              >
                {type === "START" ? "Start Compound" : type === "STOP" ? "Stop Compound" : "Dose Change"}
              </button>
            ))}
          </div>

          <AnimatePresence>
            {showLogForm && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div
                  className="rounded-xl p-5 border space-y-4"
                  style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)", boxShadow: "var(--shadow-card)" }}
                >
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Compound Name</label>
                      <input
                        type="text"
                        value={logCompound}
                        onChange={(e) => setLogCompound(e.target.value)}
                        placeholder="e.g. Testosterone Enanthate"
                        className="w-full text-sm px-3 py-2 rounded-lg border"
                        style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }}
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Class</label>
                      <select
                        value={logClass}
                        onChange={(e) => setLogClass(e.target.value)}
                        className="w-full text-sm px-3 py-2 rounded-lg border"
                        style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }}
                      >
                        <option value="anabolic">Anabolic</option>
                        <option value="ancillary">Ancillary</option>
                        <option value="peptide">Peptide</option>
                        <option value="sarm">SARM</option>
                        <option value="prescription">Prescription</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Dose (mg)</label>
                      <input
                        type="number"
                        value={logDose}
                        onChange={(e) => setLogDose(e.target.value)}
                        placeholder="500"
                        className="w-full text-sm px-3 py-2 rounded-lg border"
                        style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace" }}
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Frequency</label>
                      <input
                        type="text"
                        value={logFrequency}
                        onChange={(e) => setLogFrequency(e.target.value)}
                        placeholder="2x/week"
                        className="w-full text-sm px-3 py-2 rounded-lg border"
                        style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }}
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Route</label>
                      <select
                        value={logRoute}
                        onChange={(e) => setLogRoute(e.target.value)}
                        className="w-full text-sm px-3 py-2 rounded-lg border"
                        style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }}
                      >
                        <option value="IM">IM (Intramuscular)</option>
                        <option value="subQ">SubQ (Subcutaneous)</option>
                        <option value="oral">Oral</option>
                        <option value="transdermal">Transdermal</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleLogSubmit}
                      disabled={submitting || !logCompound}
                      className="text-sm font-medium px-5 py-2 rounded-lg text-white disabled:opacity-50"
                      style={{ background: "var(--color-accent-primary)" }}
                    >
                      {submitting ? "Logging..." : `Log ${logType.replace("_", " ")}`}
                    </button>
                    <button
                      onClick={() => setShowLogForm(false)}
                      className="text-sm px-4 py-2 rounded-lg"
                      style={{ color: "var(--color-text-muted)" }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </main>

      {/* Chat FAB */}
      {!showChat && (
        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          onClick={() => setShowChat(true)}
          className="fixed bottom-6 right-6 w-14 h-14 rounded-full flex items-center justify-center z-40 shadow-lg"
          style={{ background: "var(--color-accent-primary)" }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </motion.button>
      )}

      {/* Chat Panel */}
      <AnimatePresence>
        {showChat && (
          <Chat
            role="athlete"
            athleteId="athlete-001"
            onClose={() => setShowChat(false)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
