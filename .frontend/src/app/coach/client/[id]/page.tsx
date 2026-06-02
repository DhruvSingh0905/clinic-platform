"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { getClientDetail, setTrainingBlock, setNutritionTarget } from "@/lib/api";
import type { ClientDetail } from "@/lib/types";
import { getPhaseStyle, formatSyncTime } from "@/lib/formatters";
import Chat from "@/components/Chat";
import TabBar from "@/components/client/TabBar";
import NotesPanel from "@/components/client/NotesPanel";
import FindingsSection from "@/components/client/FindingsSection";
import VitalsSection from "@/components/client/VitalsSection";
import BloodworkSection from "@/components/client/BloodworkSection";
import TrainingSection from "@/components/client/TrainingSection";
import SubstanceSection from "@/components/client/SubstanceSection";
import NutritionSection from "@/components/client/NutritionSection";
import ConfirmationDialog from "@/components/client/ConfirmationDialog";

function getInitials(name: string) { return name.split(" ").map((n) => n[0]).join("").toUpperCase(); }

function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 bottom-0 w-60 flex flex-col z-30" style={{ background: "var(--color-bg-sidebar)", boxShadow: "var(--shadow-sidebar)" }}>
      <div className="px-5 py-6 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
        <h1 className="text-lg font-semibold" style={{ fontFamily: "'Crimson Pro', serif", color: "var(--color-text-sidebar-active)" }}>Coach Platform</h1>
        <p className="text-xs mt-0.5" style={{ color: "var(--color-text-sidebar)" }}>Cycle Data Engine</p>
      </div>
      <nav className="flex-1 py-4 px-3 space-y-1">
        <a href="/coach" className="sidebar-link flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm" style={{ color: "var(--color-text-sidebar)" }}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="2" width="5.5" height="5.5" rx="1" /><rect x="10.5" y="2" width="5.5" height="5.5" rx="1" /><rect x="2" y="10.5" width="5.5" height="5.5" rx="1" /><rect x="10.5" y="10.5" width="5.5" height="5.5" rx="1" /></svg>
          Dashboard
        </a>
        <a href="/coach" className="sidebar-link active flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm" style={{ color: "var(--color-text-sidebar-active)" }}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M13 15v-1.5a3 3 0 0 0-3-3H6a3 3 0 0 0-3 3V15" /><circle cx="8" cy="5.5" r="3" /><path d="M16 15v-1.5a3 3 0 0 0-2.25-2.9" /><path d="M12.5 2.6a3 3 0 0 1 0 5.8" /></svg>
          Clients
        </a>
      </nav>
      <div className="px-4 py-4 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium" style={{ background: "rgba(193,122,47,0.2)", color: "#C17A2F" }}>DC</div>
          <div><p className="text-xs font-medium" style={{ color: "var(--color-text-sidebar-active)" }}>Demo Coach</p><p className="text-xs" style={{ color: "var(--color-text-sidebar)" }}>coach-001</p></div>
        </div>
      </div>
    </aside>
  );
}

export default function ClientDetailPage() {
  const params = useParams();
  const router = useRouter();
  const athleteId = params.id as string;
  const [client, setClient] = useState<ClientDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [changelog, setChangelog] = useState<{type: string; actor: string; text: string; timestamp: string}[]>([]);
  const [activeTab, setActiveTab] = useState("findings");
  const [pendingConfirm, setPendingConfirm] = useState<{ text: string; onConfirm: () => Promise<void> } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [chatFindingId, setChatFindingId] = useState<string | undefined>(undefined);
  const [notesCollapsed, setNotesCollapsed] = useState(false);

  const reload = () => {
    getClientDetail("coach-001", athleteId).then(setClient).catch(() => {});
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/coach/coach-001/client/${athleteId}/changelog`)
      .then((r) => r.json()).then((d) => setChangelog(d.changelog || [])).catch(() => {});
  };

  useEffect(() => {
    let cancelled = false;
    getClientDetail("coach-001", athleteId)
      .then((data) => { if (!cancelled) { setClient(data); setLoading(false); } })
      .catch(() => { if (!cancelled) setLoading(false); });
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/coach/coach-001/client/${athleteId}/changelog`)
      .then((r) => r.json()).then((d) => { if (!cancelled) setChangelog(d.changelog || []); }).catch(() => {});
    return () => { cancelled = true; };
  }, [athleteId]);

  const handleConfirm = (text: string, action: () => Promise<void>) => {
    setPendingConfirm({ text, onConfirm: async () => { setSubmitting(true); await action(); setSubmitting(false); reload(); } });
  };

  if (loading || !client) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="ml-60 mr-80 flex-1 min-h-screen p-8" style={{ background: "var(--color-bg-primary)" }}>
          <div className="max-w-4xl mx-auto space-y-4">
            <div className="h-8 w-48 rounded animate-shimmer" style={{ background: "var(--color-bg-secondary)" }} />
            <div className="h-4 w-64 rounded animate-shimmer" style={{ background: "var(--color-bg-secondary)" }} />
            <div className="h-64 rounded-xl animate-shimmer mt-6" style={{ background: "var(--color-bg-secondary)" }} />
          </div>
        </div>
      </div>
    );
  }

  const ps = getPhaseStyle(client.phase);

  const tabs = [
    { id: "findings", label: "Findings", badge: client.findings.filter((f) => f.status === "active").length },
    { id: "vitals", label: "Vitals" },
    { id: "bloodwork", label: "Bloods" },
    { id: "training", label: "Training" },
    { id: "substance", label: "Protocol" },
    { id: "nutrition", label: "Nutrition" },
    { id: "changelog", label: "Log" },
  ];

  return (
    <div className="flex min-h-screen">
      <Sidebar />

      {/* Main content — between sidebar and notes panel */}
      <main className={`ml-60 ${notesCollapsed ? "mr-10" : "mr-80"} flex-1 min-h-screen transition-all duration-200`} style={{ background: "var(--color-bg-primary)" }}>
        <div className="max-w-4xl mx-auto px-8 py-8">
          {/* Header */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
            <button onClick={() => router.push("/coach")} className="flex items-center gap-1.5 text-sm mb-5 hover:opacity-70 transition-opacity" style={{ color: "var(--color-text-secondary)" }}>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M10 12L6 8l4-4" /></svg>
              Back to Roster
            </button>
            <div className="flex items-start gap-5 mb-8">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-lg font-semibold shrink-0" style={{ background: `${client.athlete.avatar_color}18`, color: client.athlete.avatar_color }}>
                {getInitials(client.athlete.name)}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-3 flex-wrap">
                  <h1 className="text-2xl font-semibold tracking-tight" style={{ fontFamily: "'Crimson Pro', serif" }}>{client.athlete.name}</h1>
                  <span className="text-xs font-medium px-2.5 py-1 rounded-full capitalize" style={{ background: ps.bg, color: ps.text }}>{client.phase} · Day {client.day_in_phase}</span>
                </div>
                <p className="text-sm mt-1" style={{ color: "var(--color-text-muted)" }}>Synced {formatSyncTime(client.athlete.last_sync)} · {client.athlete.integrations.join(", ")}</p>
              </div>
            </div>
          </motion.div>

          {/* Tab bar — always visible, resets sub-views on tab change */}
          <TabBar tabs={tabs} activeTab={activeTab} onTabChange={(tab) => { setActiveTab(tab); }} />

          {/* Tab content */}
          <motion.div key={activeTab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
            {activeTab === "findings" && (
              <FindingsSection
                findings={client.findings}
                wearables={client.wearables}
                labs={client.labs}
                onInvestigate={(id) => { setChatFindingId(id); setShowChat(true); }}
              />
            )}
            {activeTab === "vitals" && <VitalsSection wearables={client.wearables} />}
            {activeTab === "bloodwork" && <BloodworkSection labs={client.labs} phaseStartedAt={client.phase_started_at} />}
            {activeTab === "training" && (
              <TrainingSection
                key={`training-${activeTab}`}
                training={client.training}
                athleteId={athleteId}
                onEditBlock={() => setShowChat(true)}
              />
            )}
            {activeTab === "substance" && (
              <SubstanceSection
                substanceEvents={client.substance_events}
                drugLevels={client.drug_levels}
                athleteId={athleteId}
                role="coach"
                onConfirm={handleConfirm}
                onReload={reload}
              />
            )}
            {activeTab === "nutrition" && (
              <NutritionSection
                nutrition={client.nutrition}
                onSave={handleConfirm}
                saveNutrition={(t) => setNutritionTarget("coach-001", athleteId, t)}
              />
            )}
            {activeTab === "changelog" && (
              <div className="space-y-2">
                {changelog.length === 0 && <p className="text-sm py-8 text-center" style={{ color: "var(--color-text-muted)" }}>No changes recorded yet.</p>}
                {changelog.map((entry, i) => (
                  <div key={i} className="flex items-start gap-3 py-2.5 border-b" style={{ borderColor: "var(--color-border-card)" }}>
                    <div className="w-16 shrink-0">
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded capitalize" style={{
                        background: entry.actor === "coach" ? "var(--color-accent-light)" : "var(--color-bg-secondary)",
                        color: entry.actor === "coach" ? "var(--color-accent-primary)" : "var(--color-text-muted)",
                      }}>{entry.actor}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm" style={{ color: "var(--color-text-primary)" }}>{entry.text}</p>
                      <p className="text-[10px] mt-0.5" style={{ color: "var(--color-text-muted)", fontFamily: "'IBM Plex Mono', monospace" }}>
                        {entry.type.replace(/([A-Z])/g, " $1").trim()} · {new Date(entry.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </div>
      </main>

      {/* Notes panel — always visible */}
      <NotesPanel
        notes={client.recovery}
        athleteId={athleteId}
        onNoteAdded={reload}
        onConfirm={handleConfirm}
        collapsed={notesCollapsed}
        onToggleCollapse={() => setNotesCollapsed(!notesCollapsed)}
      />

      {/* Confirmation dialog */}
      <ConfirmationDialog pending={pendingConfirm} submitting={submitting} onCancel={() => setPendingConfirm(null)} />

      {/* Chat FAB */}
      {!showChat && (
        <motion.button initial={{ scale: 0 }} animate={{ scale: 1 }}
          onClick={() => { setChatFindingId(undefined); setShowChat(true); }}
          className="fixed bottom-6 z-40 w-14 h-14 rounded-full flex items-center justify-center shadow-lg"
          style={{ background: "var(--color-accent-primary)", right: notesCollapsed ? "calc(40px + 1.5rem)" : "calc(320px + 1.5rem)", transition: "right 0.2s" }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></svg>
        </motion.button>
      )}

      {/* Chat panel */}
      <AnimatePresence>
        {showChat && client && (
          <Chat role="coach" athleteId={athleteId} coachId="coach-001" athleteName={client.athlete.name} findingId={chatFindingId} onClose={() => setShowChat(false)} />
        )}
      </AnimatePresence>
    </div>
  );
}
