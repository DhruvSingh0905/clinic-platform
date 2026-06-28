"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { SubstanceEvent, DrugLevel } from "@/lib/types";
import { formatDate } from "@/lib/formatters";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface SubstanceSectionProps {
  substanceEvents: SubstanceEvent[];
  drugLevels: DrugLevel[];
  patientId: string;
  role: "clinician" | "patient";
  onConfirm?: (text: string, action: () => Promise<void>) => void;
  onReload?: () => void;
}

export default function SubstanceSection({ substanceEvents, drugLevels, patientId, role, onConfirm, onReload }: SubstanceSectionProps) {
  const [showForm, setShowForm] = useState(false);
  const [eventType, setEventType] = useState("START");
  const [compName, setCompName] = useState("");
  const [compClass, setCompClass] = useState("anabolic");
  const [dose, setDose] = useState("");
  const [freq, setFreq] = useState("");
  const [route, setRoute] = useState("IM");
  const [nlpInput, setNlpInput] = useState("");
  const [nlpLoading, setNlpLoading] = useState(false);

  const latestDate = drugLevels.length > 0
    ? drugLevels.reduce((max, dl) => dl.observation_date > max ? dl.observation_date : max, drugLevels[0].observation_date)
    : "";
  const latestLevels = drugLevels.filter((dl) => dl.observation_date === latestDate);

  const handleSubmit = () => {
    if (!compName) return;
    const rendered = `${eventType} ${compName}${dose ? ` ${dose}mg` : ""}${freq ? ` ${freq}` : ""}${route ? ` ${route}` : ""}`;
    const doSubmit = async () => {
      const endpoint = role === "clinician"
        ? `${API_BASE}/api/clinician/clinician-001/patient/${patientId}/substance`
        : `${API_BASE}/api/patient/${patientId}/substance`;
      await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ compound_name: compName, compound_class: compClass, event_type: eventType, dose_mg: dose ? parseFloat(dose) : undefined, frequency: freq || undefined, route: route || undefined }) });
      setShowForm(false); setCompName(""); setDose(""); setFreq("");
      onReload?.();
    };
    if (onConfirm) {
      onConfirm(role === "clinician" ? `Clinician modifying protocol: ${rendered}. Patient will be notified.` : rendered, doSubmit);
    } else { doSubmit(); }
  };

  const sendNlp = () => {
    if (!nlpInput.trim()) return;
    setNlpLoading(true);
    const chatEndpoint = role === "clinician" ? `${API_BASE}/api/clinician/clinician-001/patient/${patientId}/chat` : `${API_BASE}/api/patient/${patientId}/chat`;
    fetch(chatEndpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: nlpInput }) })
      .then((r) => r.json())
      .then(() => { setNlpInput(""); setNlpLoading(false); onReload?.(); })
      .catch(() => setNlpLoading(false));
  };

  return (
    <div className="space-y-3">
      {/* Protocol */}
      <div className="border p-4" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-[10px] uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>
            {role === "clinician" ? "Medication management" : "Your protocol · Self-reported"}
          </span>
        </div>

        {/* Timeline */}
        <div className="space-y-2 mb-4">
          {substanceEvents.map((evt, i) => (
            <div key={`${evt.compound_name}-${i}`} className="flex items-start gap-2 pl-3 border-l" style={{ borderLeftColor: "var(--color-border-emphasis)" }}>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium" style={{ color: "var(--color-text-primary)" }}>{evt.compound_name}</span>
                  <span className="text-[9px] font-medium px-1 py-0.5 uppercase" style={{ background: "var(--color-bg-hover)", color: "var(--color-text-secondary)", borderRadius: "2px" }}>{evt.compound_class === "AAS" ? "Androgen" : evt.compound_class}</span>
                </div>
                <p className="text-[11px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-secondary)" }}>
                  {evt.event_type}{evt.dose_mg ? ` · ${evt.dose_mg}mg` : ""}{evt.frequency ? ` · ${evt.frequency}` : ""}{evt.route ? ` · ${evt.route}` : ""}
                </p>
                <p className="text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{formatDate(evt.timestamp)}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Estimated levels */}
        {latestLevels.length > 0 && (
          <div>
            <p className="text-[10px] font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>Estimated Levels</p>
            <div className="space-y-2">
              {latestLevels.map((dl) => (
                <div key={dl.compound_name}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] font-medium" style={{ color: "var(--color-text-primary)" }}>{dl.compound_name}</span>
                    <span className="text-[11px] font-medium" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-secondary)" }}>
                      {Math.round(dl.level * 100)}%{dl.at_steady_state ? " (steady)" : ""}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden" style={{ background: "var(--color-border-light)", borderRadius: "1px" }}>
                    <div className="h-full" style={{ width: `${dl.level * 100}%`, background: "var(--color-accent-primary)", transition: "width 0.5s ease", borderRadius: "1px" }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Modify protocol */}
      <div className="border p-3" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
        <p className="text-[10px] font-medium mb-2 uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>Modify Protocol</p>
        <div className="flex gap-2 mb-2">
          <input type="text" value={nlpInput} onChange={(e) => setNlpInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendNlp()}
            placeholder='e.g. "add primo 400mg weekly IM" or "drop the anavar"'
            className="flex-1 text-xs px-2.5 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }} disabled={nlpLoading} />
          <button onClick={sendNlp} disabled={!nlpInput.trim() || nlpLoading} className="text-[10px] font-medium px-3 py-1.5 text-white disabled:opacity-30" style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}>
            {nlpLoading ? "..." : "Send"}
          </button>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>{showForm ? "Hide form" : "Manual form"}</button>
      </div>

      <AnimatePresence>
        {showForm && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="border p-3 space-y-2" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Compound</label>
                  <input type="text" value={compName} onChange={(e) => setCompName(e.target.value)} placeholder="Testosterone Cypionate" className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }} />
                </div>
                <div>
                  <label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Class</label>
                  <select value={compClass} onChange={(e) => setCompClass(e.target.value)} className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }}>
                    <option value="anabolic">Anabolic</option><option value="ancillary">Ancillary</option><option value="peptide">Peptide</option><option value="prescription">Prescription</option>
                  </select>
                </div>
              </div>
              {eventType !== "STOP" && (
                <div className="grid grid-cols-3 gap-2">
                  <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Dose (mg)</label><input type="number" value={dose} onChange={(e) => setDose(e.target.value)} placeholder="500" className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-primary)", borderRadius: "3px" }} /></div>
                  <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Frequency</label><input type="text" value={freq} onChange={(e) => setFreq(e.target.value)} placeholder="e3.5d" className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }} /></div>
                  <div><label className="text-[10px] font-medium block mb-0.5" style={{ color: "var(--color-text-muted)" }}>Route</label><select value={route} onChange={(e) => setRoute(e.target.value)} className="w-full text-xs px-2 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }}><option value="IM">IM</option><option value="subQ">SubQ</option><option value="oral">Oral</option><option value="transdermal">Transdermal</option></select></div>
                </div>
              )}
              <div className="flex gap-2">
                <button onClick={handleSubmit} disabled={!compName} className="text-xs font-medium px-3 py-1.5 text-white disabled:opacity-30" style={{ background: "var(--color-accent-primary)", borderRadius: "3px" }}>{role === "clinician" ? `${eventType.replace("_", " ")} (notify)` : `Log ${eventType.replace("_", " ")}`}</button>
                <button onClick={() => setShowForm(false)} className="text-xs px-2 py-1.5" style={{ color: "var(--color-text-muted)" }}>Cancel</button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
