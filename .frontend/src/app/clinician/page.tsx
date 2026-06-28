"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getRoster } from "@/lib/api";
import type { RosterEntry } from "@/lib/types";
import { getStatusStyle, formatSyncTime } from "@/lib/formatters";
import Sidebar from "@/components/Sidebar";

/* Mock data for demo */
const MOCK_ROSTER: RosterEntry[] = [
  { patient: { id: "patient-001", name: "Marcus Rivera", email: "marcus@example.com", avatar_color: "#E5534B", connected_at: "2026-03-01", last_sync: "2026-05-31T08:14:00Z", integrations: ["apple_health"] }, treatment_status: "active_treatment" },
  { patient: { id: "patient-002", name: "Elena Vasquez", email: "elena@example.com", avatar_color: "#D4952A", connected_at: "2026-02-15", last_sync: "2026-05-30T22:30:00Z", integrations: ["apple_health"] }, treatment_status: "monitoring" },
  { patient: { id: "patient-003", name: "James Okonkwo", email: "james@example.com", avatar_color: "#4C8DFF", connected_at: "2026-01-10", last_sync: "2026-05-31T06:00:00Z", integrations: ["apple_health"] }, treatment_status: "active_treatment" },
  { patient: { id: "patient-004", name: "Sarah Chen", email: "sarah@example.com", avatar_color: "#A371F7", connected_at: "2026-04-01", last_sync: "2026-05-30T19:45:00Z", integrations: ["apple_health"] }, treatment_status: "initial_consult" },
  { patient: { id: "patient-005", name: "Andre Williams", email: "andre@example.com", avatar_color: "#3FB950", connected_at: "2026-03-20", last_sync: "2026-05-29T14:20:00Z", integrations: ["apple_health"] }, treatment_status: "tapering" },
  { patient: { id: "patient-006", name: "Yuki Tanaka", email: "yuki@example.com", avatar_color: "#565B6E", connected_at: "2026-05-01", last_sync: null, integrations: ["apple_health"] }, treatment_status: "discontinued" },
];

function sortRoster(roster: RosterEntry[]): RosterEntry[] {
  return [...roster].sort((a, b) => a.patient.name.localeCompare(b.patient.name));
}

function getInitials(name: string): string {
  return name.split(" ").map((n) => n[0]).join("").toUpperCase();
}

function formatStatus(s: string): string {
  return s.replace(/_/g, " ");
}

export default function ClinicianRosterPage() {
  const router = useRouter();
  const [roster, setRoster] = useState<RosterEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;
    getRoster("clinician-001")
      .then((data) => { if (!cancelled) { setRoster(sortRoster(data)); setLoading(false); } })
      .catch(() => { if (!cancelled) { setRoster(sortRoster(MOCK_ROSTER)); setLoading(false); } });
    return () => { cancelled = true; };
  }, []);

  const filtered = search
    ? roster.filter((r) => r.patient.name.toLowerCase().includes(search.toLowerCase()))
    : roster;

  return (
    <div className="flex min-h-screen">
      <Sidebar activePage="roster" />
      <main className="ml-48 flex-1 min-h-screen" style={{ background: "var(--color-bg-primary)" }}>
        <div className="max-w-3xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h1 className="text-lg font-semibold">Patients</h1>
              <p className="text-xs mt-0.5" style={{ color: "var(--color-text-secondary)" }}>
                {roster.length} patients
              </p>
            </div>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search patients..."
              className="text-xs px-3 py-1.5 w-48 border"
              style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }}
            />
          </div>

          {/* Table header */}
          <div className="grid grid-cols-12 gap-3 px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider" style={{ color: "var(--color-text-muted)", borderBottom: "1px solid var(--color-border-light)" }}>
            <div className="col-span-6">Patient</div>
            <div className="col-span-3">Status</div>
            <div className="col-span-3 text-right">Last Sync</div>
          </div>

          {/* Rows */}
          <div>
            {loading ? (
              Array.from({ length: 4 }, (_, i) => (
                <div key={i} className="h-12 animate-shimmer" style={{ background: "var(--color-bg-secondary)" }} />
              ))
            ) : (
              filtered.map((entry) => {
                const ss = getStatusStyle(entry.treatment_status);
                return (
                  <div
                    key={entry.patient.id}
                    onClick={() => router.push(`/clinician/patient/${entry.patient.id}`)}
                    className="grid grid-cols-12 gap-3 items-center px-3 py-2.5 cursor-pointer data-row border-b"
                    style={{ borderColor: "var(--color-border-light)" }}
                  >
                    <div className="col-span-6 flex items-center gap-2 min-w-0">
                      <div className="w-7 h-7 rounded flex items-center justify-center text-[10px] font-medium shrink-0" style={{ background: `${entry.patient.avatar_color}18`, color: entry.patient.avatar_color }}>
                        {getInitials(entry.patient.name)}
                      </div>
                      <span className="text-xs font-medium truncate">{entry.patient.name}</span>
                    </div>

                    <div className="col-span-3">
                      <span className="text-[9px] font-medium px-1.5 py-0.5 capitalize" style={{ background: ss.bg, color: ss.text, borderRadius: "2px" }}>{formatStatus(entry.treatment_status)}</span>
                    </div>

                    <div className="col-span-3 text-right">
                      <span className="text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{formatSyncTime(entry.patient.last_sync)}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
