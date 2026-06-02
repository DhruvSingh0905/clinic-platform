"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { Finding, WearableMetric, LabResult } from "@/lib/types";
import { getSeverityColor, findingProvenance, formatDate, SIGNAL_TO_METRIC } from "@/lib/formatters";
import SignalChart from "./SignalChart";

interface FindingsSectionProps {
  findings: Finding[];
  wearables: WearableMetric[];
  labs: LabResult[];
  onInvestigate: (findingId: string) => void;
}

export default function FindingsSection({ findings, wearables, labs, onInvestigate }: FindingsSectionProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  function getSignalHistory(label: string): { date: string; value: number }[] {
    const metricKey = SIGNAL_TO_METRIC[label];
    if (!metricKey) return [];
    const wData = wearables.filter((w) => w.metric === metricKey).sort((a, b) => a.observation_date.localeCompare(b.observation_date)).map((w) => ({ date: w.observation_date, value: w.value_mean }));
    if (wData.length >= 2) return wData;
    const lData = labs.filter((l) => l.metric_loinc === metricKey).sort((a, b) => a.observation_date.localeCompare(b.observation_date)).map((l) => ({ date: l.observation_date, value: l.value_canonical }));
    if (lData.length >= 2) return lData;
    return [];
  }

  if (!findings.length) return <p className="text-sm py-8 text-center" style={{ color: "var(--color-text-muted)" }}>No active findings — all clear.</p>;

  return (
    <div className="space-y-4">
      {findings.map((f, i) => {
        const color = getSeverityColor(f.severity);
        const isExp = expanded.has(String(f.id));
        return (
          <motion.div key={f.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
            className="rounded-xl overflow-hidden" style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border-card)", borderLeft: `4px solid ${color}`, boxShadow: "var(--shadow-card)" }}>
            <div className="p-5">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-md" style={{ background: `${color}15`, color, border: `1px solid ${color}30` }}>{f.theme}</span>
                <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded" style={{ color }}>{f.severity}</span>
                <span className="ml-auto text-xs" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{formatDate(f.detected_at)}</span>
              </div>
              <h3 className="text-base font-semibold mb-1" style={{ fontFamily: "'Crimson Pro', serif", color: "var(--color-text-primary)" }}>{f.headline}</h3>
              <p className="text-xs mb-3" style={{ color: "var(--color-text-muted)" }}>{findingProvenance(f.theme, f.time_window_start, f.time_window_end)}</p>
              <div className="flex flex-wrap gap-3 mb-3">
                {f.signals.map((sig) => {
                  const history = getSignalHistory(sig.label);
                  const dirColor = sig.direction === "up" ? "#C44536" : sig.direction === "down" ? "#4A7FA5" : "#9B948D";
                  const arrow = sig.direction === "up" ? "↑" : sig.direction === "down" ? "↓" : "→";
                  return (
                    <div key={sig.label} className="flex items-center gap-3 px-3.5 py-2.5 rounded-lg" style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border-card)", boxShadow: "0 1px 2px rgba(0,0,0,0.03)" }}>
                      <div className="min-w-0">
                        <div className="text-[10px] font-medium uppercase tracking-wide mb-1" style={{ color: "var(--color-text-muted)" }}>{sig.label}</div>
                        <div className="flex items-baseline gap-1.5">
                          <span className="text-sm font-semibold" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-primary)" }}>{sig.value}</span>
                          <span className="text-xs font-bold" style={{ color: dirColor }}>{arrow}</span>
                        </div>
                        {sig.delta && <div className="text-[10px] mt-0.5" style={{ color: "var(--color-text-secondary)" }}>{sig.delta}</div>}
                      </div>
                      {history.length >= 2 && <SignalChart dataPoints={history} color={dirColor} width={100} height={36} />}
                    </div>
                  );
                })}
              </div>
              <div className="flex items-center gap-3">
                <button onClick={() => { const n = new Set(expanded); isExp ? n.delete(String(f.id)) : n.add(String(f.id)); setExpanded(n); }} className="text-xs underline underline-offset-2" style={{ color: "var(--color-text-secondary)" }}>{isExp ? "Hide details" : "Show details"}</button>
                <button onClick={() => onInvestigate(String(f.id))} className="text-xs font-medium px-3 py-1.5 rounded-lg inline-flex items-center gap-1.5" style={{ background: "rgba(193,122,47,0.08)", color: "var(--color-accent-primary)" }}>
                  <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M14 10a1.5 1.5 0 0 1-1.5 1.5H5L2 14.5V4A1.5 1.5 0 0 1 3.5 2.5h9A1.5 1.5 0 0 1 14 4z" /></svg>
                  Ask about this
                </button>
              </div>
              <AnimatePresence>{isExp && (<motion.p initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="text-sm mt-3 leading-relaxed overflow-hidden" style={{ color: "var(--color-text-secondary)" }}>{f.summary}</motion.p>)}</AnimatePresence>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
