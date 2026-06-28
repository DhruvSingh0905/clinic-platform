"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AnimatePresence } from "framer-motion";
import { getPatientDetail, setTrainingBlock, setNutritionTarget } from "@/lib/api";
import type { PatientDetail } from "@/lib/types";
import { getStatusStyle, formatSyncTime } from "@/lib/formatters";
import Chat from "@/components/Chat";
import Sidebar from "@/components/Sidebar";
import TabBar from "@/components/client/TabBar";
import NotesPanel from "@/components/client/NotesPanel";
// FindingsSection disconnected — can be re-enabled later
// import FindingsSection from "@/components/client/FindingsSection";
import VitalsSection from "@/components/client/VitalsSection";
import BloodworkSection from "@/components/client/BloodworkSection";
import TrainingSection from "@/components/client/TrainingSection";
import SubstanceSection from "@/components/client/SubstanceSection";
import NutritionSection from "@/components/client/NutritionSection";
import ConfirmationDialog from "@/components/client/ConfirmationDialog";
import DocumentsSection from "@/components/client/DocumentsSection";
import AssessmentSection from "@/components/client/AssessmentSection";
import FollowUpSection from "@/components/client/FollowUpSection";

function getInitials(name: string) { return name.split(" ").map((n) => n[0]).join("").toUpperCase(); }

export default function PatientDetailPage() {
  const params = useParams();
  const router = useRouter();
  const patientId = params.id as string;
  const [patient, setPatient] = useState<PatientDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [changelog, setChangelog] = useState<{type: string; actor: string; text: string; timestamp: string}[]>([]);
  const [activeTab, setActiveTab] = useState("vitals");
  const [pendingConfirm, setPendingConfirm] = useState<{ text: string; onConfirm: () => Promise<void> } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [notesCollapsed, setNotesCollapsed] = useState(false);

  const reload = () => {
    getPatientDetail("clinician-001", patientId).then(setPatient).catch(() => {});
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/clinician/clinician-001/patient/${patientId}/changelog`)
      .then((r) => r.json()).then((d) => setChangelog(d.changelog || [])).catch(() => {});
  };

  useEffect(() => {
    let cancelled = false;
    getPatientDetail("clinician-001", patientId)
      .then((data) => { if (!cancelled) { setPatient(data); setLoading(false); } })
      .catch(() => { if (!cancelled) setLoading(false); });
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"}/api/clinician/clinician-001/patient/${patientId}/changelog`)
      .then((r) => r.json()).then((d) => { if (!cancelled) setChangelog(d.changelog || []); }).catch(() => {});
    return () => { cancelled = true; };
  }, [patientId]);

  const handleConfirm = (text: string, action: () => Promise<void>) => {
    setPendingConfirm({ text, onConfirm: async () => { setSubmitting(true); await action(); setSubmitting(false); reload(); } });
  };

  if (loading || !patient) {
    return (
      <div className="flex min-h-screen">
        <Sidebar activePage="client" />
        <div className="ml-48 mr-72 flex-1 min-h-screen p-6" style={{ background: "var(--color-bg-primary)" }}>
          <div className="max-w-3xl mx-auto space-y-3">
            <div className="h-6 w-40 animate-shimmer" style={{ background: "var(--color-bg-secondary)" }} />
            <div className="h-4 w-56 animate-shimmer" style={{ background: "var(--color-bg-secondary)" }} />
            <div className="h-48 mt-4 animate-shimmer" style={{ background: "var(--color-bg-secondary)" }} />
          </div>
        </div>
      </div>
    );
  }

  const ss = getStatusStyle(patient.treatment_status);

  const tabs = [
    { id: "vitals", label: "Vitals" },
    { id: "bloodwork", label: "Bloods" },
    { id: "substance", label: "Meds" },
    { id: "assessment", label: "Notes" },
    { id: "followup", label: "Follow-up" },
    { id: "training", label: "Activity" },
    { id: "nutrition", label: "Nutrition" },
    { id: "documents", label: "Docs" },
    { id: "changelog", label: "Log" },
  ];

  return (
    <div className="flex min-h-screen">
      <Sidebar activePage="client" />

      <main className={`ml-48 ${notesCollapsed ? "mr-8" : "mr-72"} flex-1 min-h-screen transition-all duration-150`} style={{ background: "var(--color-bg-primary)" }}>
        <div className="max-w-3xl mx-auto px-6 py-6">
          {/* Header */}
          <div>
            <button onClick={() => router.push("/clinician")} className="flex items-center gap-1 text-[10px] mb-3 hover:opacity-70" style={{ color: "var(--color-text-muted)" }}>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M8 9L4 6l4-3" /></svg>
              Back to Roster
            </button>
            <div className="flex items-start gap-3 mb-5">
              <div className="w-10 h-10 rounded flex items-center justify-center text-sm font-medium shrink-0" style={{ background: `${patient.patient.avatar_color}18`, color: patient.patient.avatar_color }}>
                {getInitials(patient.patient.name)}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h1 className="text-lg font-semibold">{patient.patient.name}</h1>
                  <span className="text-[9px] font-medium px-1.5 py-0.5 capitalize" style={{ background: ss.bg, color: ss.text, borderRadius: "2px" }}>{patient.treatment_status.replace(/_/g, " ")}{patient.treatment_days ? ` · ${patient.treatment_days}d` : ""}</span>
                </div>
                <p className="text-[10px] mt-0.5" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>
                  {formatSyncTime(patient.patient.last_sync)} · {patient.patient.integrations.join(", ")}
                </p>
              </div>
            </div>
          </div>

          <TabBar tabs={tabs} activeTab={activeTab} onTabChange={(tab) => setActiveTab(tab)} />

          <div key={activeTab}>
            {activeTab === "vitals" && <VitalsSection wearables={patient.wearables} />}
            {activeTab === "bloodwork" && <BloodworkSection labs={patient.labs} />}
            {activeTab === "documents" && <DocumentsSection patientId={patientId} />}
            {activeTab === "training" && (
              <TrainingSection key={`training-${activeTab}`} training={patient.training} patientId={patientId} onEditBlock={() => setShowChat(true)} />
            )}
            {activeTab === "substance" && (
              <SubstanceSection substanceEvents={patient.substance_events} drugLevels={patient.drug_levels} patientId={patientId} role="clinician" onConfirm={handleConfirm} onReload={reload} />
            )}
            {activeTab === "assessment" && (
              <AssessmentSection patientId={patientId} notes={patient.recovery} onNoteAdded={reload} />
            )}
            {activeTab === "followup" && (
              <FollowUpSection patientId={patientId} />
            )}
            {activeTab === "nutrition" && (
              <NutritionSection nutrition={patient.nutrition} onSave={handleConfirm} saveNutrition={(t) => setNutritionTarget("clinician-001", patientId, t)} />
            )}
            {activeTab === "changelog" && (
              <div className="space-y-0">
                {changelog.length === 0 && <p className="text-xs py-6 text-center" style={{ color: "var(--color-text-muted)" }}>No changes recorded.</p>}
                {changelog.map((entry, i) => (
                  <div key={i} className="flex items-start gap-3 py-2 border-b" style={{ borderColor: "var(--color-border-light)" }}>
                    <span className="text-[9px] font-medium px-1.5 py-0.5 uppercase shrink-0" style={{
                      background: entry.actor === "clinician" ? "var(--color-accent-light)" : "var(--color-bg-hover)",
                      color: entry.actor === "clinician" ? "var(--color-accent-primary)" : "var(--color-text-muted)",
                      borderRadius: "2px",
                    }}>{entry.actor}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs" style={{ color: "var(--color-text-primary)" }}>{entry.text}</p>
                      <p className="text-[10px] mt-0.5" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>
                        {entry.type.replace(/([A-Z])/g, " $1").trim()} · {new Date(entry.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>

      <NotesPanel notes={patient.recovery} patientId={patientId} onNoteAdded={reload} onConfirm={handleConfirm} collapsed={notesCollapsed} onToggleCollapse={() => setNotesCollapsed(!notesCollapsed)} />

      <ConfirmationDialog pending={pendingConfirm} submitting={submitting} onCancel={() => setPendingConfirm(null)} />

      {/* Chat FAB */}
      {!showChat && (
        <button
          onClick={() => setShowChat(true)}
          className="fixed bottom-4 z-40 w-10 h-10 rounded flex items-center justify-center"
          style={{ background: "var(--color-accent-primary)", right: notesCollapsed ? "calc(32px + 1rem)" : "calc(288px + 1rem)", transition: "right 0.15s" }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="white" strokeWidth="1.5" strokeLinecap="round"><path d="M15.75 11.25a1.5 1.5 0 0 1-1.5 1.5H5.25l-3 3V3.75a1.5 1.5 0 0 1 1.5-1.5h10.5a1.5 1.5 0 0 1 1.5 1.5z" /></svg>
        </button>
      )}

      <AnimatePresence>
        {showChat && patient && (
          <Chat role="clinician" patientId={patientId} clinicianId="clinician-001" patientName={patient.patient.name} onClose={() => setShowChat(false)} />
        )}
      </AnimatePresence>
    </div>
  );
}
