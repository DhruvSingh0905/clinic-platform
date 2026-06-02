"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { getRoster } from "@/lib/api";
import type { RosterEntry, Finding } from "@/lib/types";

/* ── Mock data for demo ── */
const MOCK_ROSTER: RosterEntry[] = [
  {
    athlete: { id: "athlete-001", name: "Marcus Rivera", email: "marcus@example.com", avatar_color: "#C44536", connected_at: "2026-03-01", last_sync: "2026-05-31T08:14:00Z", integrations: ["apple_health", "bloodwork"] },
    top_finding: { id: "f1", detector_id: "lipid_shift", theme: "Lipid Panel", severity: "concerning", headline: "LDL surged 42% over 6 weeks", summary: "LDL cholesterol rose from 112 to 159 mg/dL coinciding with blast phase onset. HDL declined 18%.", signals: [{ label: "LDL", value: "159 mg/dL", direction: "up", delta: "+42%" }, { label: "HDL", value: "38 mg/dL", direction: "down", delta: "-18%" }], detected_at: "2026-05-30", status: "active" },
    finding_count: 3, phase: "blast", day_in_phase: 28,
  },
  {
    athlete: { id: "athlete-002", name: "Elena Vasquez", email: "elena@example.com", avatar_color: "#C98B2F", connected_at: "2026-02-15", last_sync: "2026-05-30T22:30:00Z", integrations: ["apple_health", "bloodwork", "withings"] },
    top_finding: { id: "f2", detector_id: "cardiac_drift", theme: "Cardiac", severity: "notable", headline: "Resting HR elevated 8 bpm above baseline", summary: "14-day resting HR mean shifted from 54 to 62 bpm. HRV declined proportionally.", signals: [{ label: "RHR", value: "62 bpm", direction: "up", delta: "+8 bpm" }, { label: "HRV", value: "34 ms", direction: "down", delta: "-12 ms" }], detected_at: "2026-05-29", status: "active" },
    finding_count: 2, phase: "blast", day_in_phase: 42,
  },
  {
    athlete: { id: "athlete-003", name: "James Okonkwo", email: "james@example.com", avatar_color: "#4A7FA5", connected_at: "2026-01-10", last_sync: "2026-05-31T06:00:00Z", integrations: ["apple_health"] },
    top_finding: { id: "f3", detector_id: "recovery_quality", theme: "Recovery", severity: "info", headline: "Sleep quality trending below baseline", summary: "7-day sleep efficiency dropped to 82%. Deep sleep proportion decreased.", signals: [{ label: "Sleep Eff.", value: "82%", direction: "down", delta: "-6%" }], detected_at: "2026-05-28", status: "active" },
    finding_count: 1, phase: "cruise", day_in_phase: 14,
  },
  {
    athlete: { id: "athlete-004", name: "Sarah Chen", email: "sarah@example.com", avatar_color: "#7B68AE", connected_at: "2026-04-01", last_sync: "2026-05-30T19:45:00Z", integrations: ["apple_health", "bloodwork"] },
    top_finding: null,
    finding_count: 0, phase: "prep", day_in_phase: 56,
  },
  {
    athlete: { id: "athlete-005", name: "Andre Williams", email: "andre@example.com", avatar_color: "#5A8A5C", connected_at: "2026-03-20", last_sync: "2026-05-29T14:20:00Z", integrations: ["apple_health", "withings"] },
    top_finding: null,
    finding_count: 0, phase: "offseason", day_in_phase: 8,
  },
  {
    athlete: { id: "athlete-006", name: "Yuki Tanaka", email: "yuki@example.com", avatar_color: "#9B948D", connected_at: "2026-05-01", last_sync: null, integrations: ["apple_health"] },
    top_finding: null,
    finding_count: 0, phase: "off", day_in_phase: 0,
  },
];

const SEVERITY_ORDER: Record<string, number> = { concerning: 0, notable: 1, info: 2 };

function sortRoster(roster: RosterEntry[]): RosterEntry[] {
  return [...roster].sort((a, b) => {
    const sa = a.top_finding ? SEVERITY_ORDER[a.top_finding.severity] ?? 3 : 99;
    const sb = b.top_finding ? SEVERITY_ORDER[b.top_finding.severity] ?? 3 : 99;
    if (sa !== sb) return sa - sb;
    return b.finding_count - a.finding_count;
  });
}

function getPhaseStyle(phase: string): { bg: string; text: string } {
  switch (phase) {
    case "blast": return { bg: "rgba(196, 69, 54, 0.1)", text: "#C44536" };
    case "cruise": return { bg: "rgba(74, 127, 165, 0.1)", text: "#4A7FA5" };
    case "prep": return { bg: "rgba(123, 104, 174, 0.1)", text: "#7B68AE" };
    case "offseason": return { bg: "rgba(90, 138, 92, 0.1)", text: "#5A8A5C" };
    case "off": return { bg: "rgba(155, 148, 141, 0.1)", text: "#9B948D" };
    default: return { bg: "rgba(155, 148, 141, 0.1)", text: "#9B948D" };
  }
}

function getSeverityColor(severity: Finding["severity"]): string {
  switch (severity) {
    case "concerning": return "#C44536";
    case "notable": return "#C98B2F";
    case "info": return "#4A7FA5";
  }
}

function getInitials(name: string): string {
  return name.split(" ").map((n) => n[0]).join("").toUpperCase();
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

function integrationIcon(name: string) {
  switch (name) {
    case "apple_health":
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 1.5C5.5 1.5 4.5 2.5 4.5 2.5S3.5 1 2 1.5C0.5 2 0.5 4 1.5 5.5S4.5 9 7 12c2.5-3 5-5.5 5.5-6.5S8.5 2 7 2.5" stroke="#9B948D" strokeWidth="1" strokeLinecap="round" />
        </svg>
      );
    case "bloodwork":
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 1L4 7a3 3 0 1 0 6 0L7 1z" stroke="#9B948D" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "withings":
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <rect x="2" y="4" width="10" height="7" rx="1" stroke="#9B948D" strokeWidth="1" />
          <path d="M5 4V3a2 2 0 0 1 4 0v1" stroke="#9B948D" strokeWidth="1" />
        </svg>
      );
    default: return null;
  }
}

/* ── Skeleton ── */
function SkeletonCard() {
  return (
    <div className="rounded-xl p-5 border" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)" }}>
      <div className="flex items-center gap-4">
        <div className="w-11 h-11 rounded-full animate-shimmer" style={{ background: "var(--color-bg-secondary)" }} />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-32 rounded animate-shimmer" style={{ background: "var(--color-bg-secondary)" }} />
          <div className="h-3 w-48 rounded animate-shimmer" style={{ background: "var(--color-bg-secondary)" }} />
        </div>
      </div>
    </div>
  );
}

/* ── Sidebar ── */
function Sidebar() {
  return (
    <aside
      className="fixed left-0 top-0 bottom-0 w-60 flex flex-col z-30"
      style={{
        background: "var(--color-bg-sidebar)",
        boxShadow: "var(--shadow-sidebar)",
      }}
    >
      {/* Logo */}
      <div className="px-5 py-6 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
        <h1
          className="text-lg font-semibold"
          style={{ fontFamily: "'Crimson Pro', serif", color: "var(--color-text-sidebar-active)" }}
        >
          Coach Platform
        </h1>
        <p className="text-xs mt-0.5" style={{ color: "var(--color-text-sidebar)" }}>
          Cycle Data Engine
        </p>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-3 space-y-1">
        <a href="/coach" className="sidebar-link active flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm" style={{ color: "var(--color-text-sidebar-active)" }}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="2" width="5.5" height="5.5" rx="1" />
            <rect x="10.5" y="2" width="5.5" height="5.5" rx="1" />
            <rect x="2" y="10.5" width="5.5" height="5.5" rx="1" />
            <rect x="10.5" y="10.5" width="5.5" height="5.5" rx="1" />
          </svg>
          Dashboard
        </a>
        <a href="/coach" className="sidebar-link flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm" style={{ color: "var(--color-text-sidebar)" }}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M13 15v-1.5a3 3 0 0 0-3-3H6a3 3 0 0 0-3 3V15" />
            <circle cx="8" cy="5.5" r="3" />
            <path d="M16 15v-1.5a3 3 0 0 0-2.25-2.9" />
            <path d="M12.5 2.6a3 3 0 0 1 0 5.8" />
          </svg>
          Clients
        </a>
        <a href="/coach" className="sidebar-link flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm" style={{ color: "var(--color-text-sidebar)" }}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="9" cy="9" r="7" />
            <path d="M9 5.5v4l2.5 1.5" />
          </svg>
          Settings
        </a>
      </nav>

      {/* Coach profile */}
      <div className="px-4 py-4 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium"
            style={{ background: "rgba(193, 122, 47, 0.2)", color: "#C17A2F" }}
          >
            DC
          </div>
          <div>
            <p className="text-xs font-medium" style={{ color: "var(--color-text-sidebar-active)" }}>Demo Coach</p>
            <p className="text-xs" style={{ color: "var(--color-text-sidebar)" }}>coach-001</p>
          </div>
        </div>
      </div>
    </aside>
  );
}

/* ── Main Page ── */
export default function CoachRosterPage() {
  const router = useRouter();
  const [roster, setRoster] = useState<RosterEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getRoster("coach-001")
      .then((data) => {
        if (!cancelled) {
          setRoster(sortRoster(data));
          setLoading(false);
        }
      })
      .catch(() => {
        // Fallback to mock data in demo mode
        if (!cancelled) {
          setRoster(sortRoster(MOCK_ROSTER));
          setLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, []);

  const needsAttention = roster.filter((r) => r.top_finding && r.top_finding.severity !== "info").length;

  return (
    <div className="flex min-h-screen">
      <Sidebar />

      {/* Main content */}
      <main className="ml-60 flex-1 min-h-screen" style={{ background: "var(--color-bg-primary)" }}>
        <div className="max-w-4xl mx-auto px-8 py-10">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <h1
              className="text-3xl font-semibold tracking-tight"
              style={{ fontFamily: "'Crimson Pro', serif" }}
            >
              Your Roster
            </h1>
            <p className="mt-1.5 text-sm" style={{ color: "var(--color-text-secondary)" }}>
              {roster.length} athletes{needsAttention > 0 && (
                <span> — <span style={{ color: "var(--color-severity-concerning)" }}>{needsAttention} need attention</span></span>
              )}
            </p>
          </motion.div>

          {/* Roster */}
          <div className="mt-8 space-y-3">
            {loading ? (
              <>
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
              </>
            ) : (
              roster.map((entry, i) => {
                const ps = getPhaseStyle(entry.phase);
                return (
                  <motion.div
                    key={entry.athlete.id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.35, delay: i * 0.06 }}
                    onClick={() => router.push(`/coach/client/${entry.athlete.id}`)}
                    className="group cursor-pointer rounded-xl border overflow-hidden"
                    style={{
                      borderColor: "var(--color-border-card)",
                      background: "var(--color-bg-card)",
                      boxShadow: "var(--shadow-card)",
                      transition: "box-shadow 0.2s ease, border-color 0.2s ease",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.boxShadow = "var(--shadow-elevated)";
                      e.currentTarget.style.borderColor = "var(--color-border-light)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = "var(--shadow-card)";
                      e.currentTarget.style.borderColor = "var(--color-border-card)";
                    }}
                  >
                    <div className="flex items-start p-5 gap-4">
                      {/* Avatar */}
                      <div
                        className="w-11 h-11 rounded-full flex items-center justify-center text-sm font-medium shrink-0"
                        style={{ background: `${entry.athlete.avatar_color}18`, color: entry.athlete.avatar_color }}
                      >
                        {getInitials(entry.athlete.name)}
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="text-sm font-medium" style={{ color: "var(--color-text-primary)" }}>
                            {entry.athlete.name}
                          </span>
                          <span
                            className="text-xs font-medium px-2 py-0.5 rounded-full capitalize"
                            style={{ background: ps.bg, color: ps.text }}
                          >
                            {entry.phase}{entry.day_in_phase > 0 && ` · Day ${entry.day_in_phase}`}
                          </span>
                          <div className="flex items-center gap-1.5 ml-auto">
                            {entry.athlete.integrations.map((intg) => (
                              <span key={intg} title={intg}>{integrationIcon(intg)}</span>
                            ))}
                          </div>
                        </div>

                        {/* Sync time */}
                        <p className="text-xs mt-1" style={{ color: "var(--color-text-muted)" }}>
                          Synced {formatSyncTime(entry.athlete.last_sync)}
                        </p>

                        {/* Top finding */}
                        {entry.top_finding && (
                          <div
                            className="mt-3 rounded-lg border-l-[3px] p-3"
                            style={{
                              borderLeftColor: getSeverityColor(entry.top_finding.severity),
                              background: entry.top_finding.severity === "concerning"
                                ? "var(--color-severity-concerning-bg)"
                                : entry.top_finding.severity === "notable"
                                ? "var(--color-severity-notable-bg)"
                                : "var(--color-severity-info-bg)",
                            }}
                          >
                            <p className="text-xs font-medium" style={{ color: getSeverityColor(entry.top_finding.severity) }}>
                              {entry.top_finding.theme}
                            </p>
                            <p className="text-sm mt-0.5" style={{ color: "var(--color-text-primary)" }}>
                              {entry.top_finding.headline}
                            </p>
                            {/* Signal badges */}
                            <div className="flex flex-wrap gap-2 mt-2">
                              {entry.top_finding.signals.map((sig) => (
                                <span
                                  key={sig.label}
                                  className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-md"
                                  style={{
                                    fontFamily: "'IBM Plex Mono', monospace",
                                    background: "rgba(0,0,0,0.03)",
                                    color: "var(--color-text-secondary)",
                                  }}
                                >
                                  <span style={{ color: "var(--color-text-muted)" }}>{sig.label}</span>
                                  {sig.value}
                                  {sig.direction && (
                                    <span style={{ color: sig.direction === "up" ? "#C44536" : sig.direction === "down" ? "#4A7FA5" : "#9B948D" }}>
                                      {sig.direction === "up" ? "\u2191" : sig.direction === "down" ? "\u2193" : "\u2192"}
                                    </span>
                                  )}
                                  {sig.delta && <span style={{ color: "var(--color-text-muted)" }}>{sig.delta}</span>}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Finding count badge */}
                      {entry.finding_count > 0 && (
                        <div
                          className="shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium"
                          style={{
                            background: entry.top_finding
                              ? `${getSeverityColor(entry.top_finding.severity)}15`
                              : "var(--color-bg-secondary)",
                            color: entry.top_finding
                              ? getSeverityColor(entry.top_finding.severity)
                              : "var(--color-text-muted)",
                          }}
                        >
                          {entry.finding_count}
                        </div>
                      )}
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
