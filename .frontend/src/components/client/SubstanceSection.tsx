"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { SubstanceEvent, DrugLevel } from "@/lib/types";
import { formatDate } from "@/lib/formatters";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface SubstanceSectionProps {
  substanceEvents: SubstanceEvent[];
  drugLevels: DrugLevel[];
  athleteId: string;
  role: "coach" | "athlete";
  onConfirm?: (text: string, action: () => Promise<void>) => void;
  onReload?: () => void;
}

export default function SubstanceSection({ substanceEvents, drugLevels, athleteId, role, onConfirm, onReload }: SubstanceSectionProps) {
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
      const endpoint = role === "coach"
        ? `${API_BASE}/api/coach/coach-001/client/${athleteId}/substance`
        : `${API_BASE}/api/athlete/${athleteId}/substance`;
      await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ compound_name: compName, compound_class: compClass, event_type: eventType, dose_mg: dose ? parseFloat(dose) : undefined, frequency: freq || undefined, route: route || undefined }),
      });
      setShowForm(false);
      setCompName(""); setDose(""); setFreq("");
      onReload?.();
    };
    if (onConfirm) {
      onConfirm(role === "coach" ? `Coach modifying protocol: ${rendered}. Athlete will be notified.` : rendered, doSubmit);
    } else {
      doSubmit();
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-xl p-5" style={{ background: "var(--color-bg-secondary)" }}>
        <div className="flex items-center gap-2 mb-4">
          {role === "coach" ? (
            <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>Protocol management · Athlete will be notified of changes</span>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="6" width="8" height="6" rx="1" /><path d="M5 6V4.5a2 2 0 0 1 4 0V6" />
              </svg>
              <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>Your protocol · Self-reported</span>
            </>
          )}
        </div>

        {/* Timeline */}
        <div className="space-y-3 mb-5">
          {substanceEvents.map((evt, i) => (
            <div key={`${evt.compound_name}-${i}`} className="flex items-start gap-3 pl-4 border-l-2" style={{ borderLeftColor: "var(--color-border-light)" }}>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>{evt.compound_name}</span>
                  <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: "rgba(0,0,0,0.04)", color: "var(--color-text-muted)" }}>{evt.compound_class}</span>
                </div>
                <p className="text-xs mt-0.5" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>
                  {evt.event_type}{evt.dose_mg ? ` · ${evt.dose_mg}mg` : ""}{evt.frequency ? ` · ${evt.frequency}` : ""}{evt.route ? ` · ${evt.route}` : ""}
                </p>
                <p className="text-xs mt-0.5" style={{ color: "var(--color-text-muted)" }}>{formatDate(evt.timestamp)}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Estimated levels */}
        {latestLevels.length > 0 && (
          <div>
            <p className="text-xs font-medium mb-3 uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>Estimated Levels (from logged protocol)</p>
            <div className="space-y-3">
              {latestLevels.map((dl) => (
                <div key={dl.compound_name}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs" style={{ color: "var(--color-text-secondary)" }}>{dl.compound_name}</span>
                    <span className="text-xs" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>
                      {Math.round(dl.level * 100)}%{dl.at_steady_state ? " (steady)" : ""}
                    </span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--color-border-light)" }}>
                    <div className="h-full rounded-full" style={{ width: `${dl.level * 100}%`, background: dl.compound_class === "anabolic" ? "var(--color-accent-primary)" : "var(--color-text-muted)", transition: "width 0.5s ease" }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Protocol change — natural language OR form */}
      <div className="rounded-xl p-4 border" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)" }}>
        <p className="text-xs font-medium mb-2" style={{ color: "var(--color-text-secondary)" }}>Modify Protocol</p>
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={nlpInput}
            onChange={(e) => setNlpInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && nlpInput.trim()) {
                setNlpLoading(true);
                const chatEndpoint = role === "coach"
                  ? `${API_BASE}/api/coach/coach-001/client/${athleteId}/chat`
                  : `${API_BASE}/api/athlete/${athleteId}/chat`;
                fetch(chatEndpoint, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ message: nlpInput }),
                })
                  .then((r) => r.json())
                  .then(() => { setNlpInput(""); setNlpLoading(false); onReload?.(); })
                  .catch(() => setNlpLoading(false));
              }
            }}
            placeholder="e.g. &quot;add primo 400mg weekly IM&quot; or &quot;drop the anavar&quot;"
            className="flex-1 text-sm px-3 py-2 rounded-lg border"
            style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }}
            disabled={nlpLoading}
          />
          <button
            onClick={() => {
              if (!nlpInput.trim()) return;
              setNlpLoading(true);
              const chatEndpoint = role === "coach"
                ? `${API_BASE}/api/coach/coach-001/client/${athleteId}/chat`
                : `${API_BASE}/api/athlete/${athleteId}/chat`;
              fetch(chatEndpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: nlpInput }),
              })
                .then((r) => r.json())
                .then(() => { setNlpInput(""); setNlpLoading(false); onReload?.(); })
                .catch(() => setNlpLoading(false));
            }}
            disabled={!nlpInput.trim() || nlpLoading}
            className="text-xs font-medium px-4 py-2 rounded-lg text-white disabled:opacity-50"
            style={{ background: "var(--color-accent-primary)" }}
          >
            {nlpLoading ? "Processing..." : "Send"}
          </button>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="text-[10px] underline" style={{ color: "var(--color-text-muted)" }}>
          {showForm ? "Hide manual form" : "Or use manual form"}
        </button>
      </div>

      <AnimatePresence>
        {showForm && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="rounded-xl p-4 border space-y-3" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)" }}>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Compound</label>
                  <input type="text" value={compName} onChange={(e) => setCompName(e.target.value)} placeholder="e.g. Testosterone Cypionate" className="w-full text-sm px-3 py-2 rounded-lg border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }} />
                </div>
                <div>
                  <label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Class</label>
                  <select value={compClass} onChange={(e) => setCompClass(e.target.value)} className="w-full text-sm px-3 py-2 rounded-lg border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }}>
                    <option value="anabolic">Anabolic</option><option value="ancillary">Ancillary</option><option value="peptide">Peptide</option><option value="prescription">Prescription</option>
                  </select>
                </div>
              </div>
              {eventType !== "STOP" && (
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Dose (mg)</label>
                    <input type="number" value={dose} onChange={(e) => setDose(e.target.value)} placeholder="500" className="w-full text-sm px-3 py-2 rounded-lg border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", fontFamily: "'IBM Plex Mono', monospace" }} />
                  </div>
                  <div>
                    <label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Frequency</label>
                    <input type="text" value={freq} onChange={(e) => setFreq(e.target.value)} placeholder="e3.5d" className="w-full text-sm px-3 py-2 rounded-lg border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }} />
                  </div>
                  <div>
                    <label className="text-xs font-medium block mb-1" style={{ color: "var(--color-text-secondary)" }}>Route</label>
                    <select value={route} onChange={(e) => setRoute(e.target.value)} className="w-full text-sm px-3 py-2 rounded-lg border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)" }}>
                      <option value="IM">IM</option><option value="subQ">SubQ</option><option value="oral">Oral</option><option value="transdermal">Transdermal</option>
                    </select>
                  </div>
                </div>
              )}
              <div className="flex gap-3">
                <button onClick={handleSubmit} disabled={!compName} className="text-sm font-medium px-4 py-2 rounded-lg text-white disabled:opacity-50" style={{ background: "var(--color-accent-primary)" }}>
                  {role === "coach" ? `${eventType.replace("_", " ")} (notify athlete)` : `Log ${eventType.replace("_", " ")}`}
                </button>
                <button onClick={() => setShowForm(false)} className="text-sm px-3 py-2 rounded-lg" style={{ color: "var(--color-text-muted)" }}>Cancel</button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
