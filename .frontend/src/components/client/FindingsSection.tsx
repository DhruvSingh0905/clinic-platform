"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { Finding, WearableMetric, LabResult } from "@/lib/types";
import { getSeverityColor, findingProvenance, formatDate, SIGNAL_TO_METRIC } from "@/lib/formatters";
import SignalChart from "./SignalChart";

interface FindingsSectionProps {
  findings: Finding[];
  wearables: WearableMetric[];
  labs: LabResult[];
  onInvestigate: (finding: Finding) => void;
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

  if (!findings.length) return <p className="text-xs py-6 text-center" style={{ color: "var(--color-text-muted)" }}>No active findings.</p>;

  return (
    <div className="space-y-2">
      {findings.map((f) => {
        const color = getSeverityColor(f.severity);
        const isExp = expanded.has(String(f.id));
        return (
          <div
            key={f.id}
            className="border-l-2 border"
            style={{ borderColor: "var(--color-border-light)", borderLeftColor: color, background: "var(--color-bg-card)", borderRadius: "3px" }}
          >
            <div className="px-4 py-3">
              {/* Header row */}
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color }}>{f.theme}</span>
                <span className="text-[10px] uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>{f.severity}</span>
                <span className="ml-auto text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{formatDate(f.detected_at)}</span>
              </div>

              {/* Headline */}
              <h3 className="text-sm font-medium mb-1" style={{ color: "var(--color-text-primary)" }}>{f.headline}</h3>
              <p className="text-[10px] mb-3 uppercase tracking-wide" style={{ color: "var(--color-text-muted)" }}>{findingProvenance(f.theme, f.time_window_start, f.time_window_end)}</p>

              {/* Signals */}
              <div className="flex flex-wrap gap-2 mb-3">
                {f.signals.map((sig) => {
                  const history = getSignalHistory(sig.label);
                  const dirColor = sig.direction === "up" ? "#E5534B" : sig.direction === "down" ? "#4C8DFF" : "var(--color-text-muted)";
                  const arrow = sig.direction === "up" ? "\u2191" : sig.direction === "down" ? "\u2193" : "\u2192";
                  return (
                    <div key={sig.label} className="flex items-center gap-2.5 px-2.5 py-1.5 border" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-secondary)", borderRadius: "3px" }}>
                      <div>
                        <div className="text-[9px] font-medium uppercase tracking-wider mb-0.5" style={{ color: "var(--color-text-muted)" }}>{sig.label}</div>
                        <div className="flex items-baseline gap-1">
                          <span className="text-xs font-medium" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-primary)" }}>{sig.value}</span>
                          <span className="text-xs font-semibold" style={{ color: dirColor }}>{arrow}</span>
                        </div>
                        {sig.delta && <div className="text-[9px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{sig.delta}</div>}
                      </div>
                      {history.length >= 2 && <SignalChart dataPoints={history} color={dirColor} width={80} height={28} />}
                    </div>
                  );
                })}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2">
                <button onClick={() => { const n = new Set(expanded); isExp ? n.delete(String(f.id)) : n.add(String(f.id)); setExpanded(n); }} className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>{isExp ? "Hide" : "Details"}</button>
                <button onClick={() => onInvestigate(f)} className="text-[10px] font-medium px-2 py-1 inline-flex items-center gap-1" style={{ background: "var(--color-accent-light)", color: "var(--color-accent-primary)", borderRadius: "3px" }}>
                  <svg width="10" height="10" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M12 9a1.5 1.5 0 0 1-1.5 1.5H4.5L2 12.5V3.5A1.5 1.5 0 0 1 3.5 2h7A1.5 1.5 0 0 1 12 3.5z" /></svg>
                  Investigate
                </button>
              </div>

              <AnimatePresence>
                {isExp && (
                  <motion.p initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="text-xs mt-2 leading-relaxed overflow-hidden" style={{ color: "var(--color-text-secondary)" }}>
                    {f.summary}
                  </motion.p>
                )}
              </AnimatePresence>
            </div>
          </div>
        );
      })}
    </div>
  );
}
