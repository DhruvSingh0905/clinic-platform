"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { LabResult } from "@/lib/types";
import { getFlagColor, formatDateShort } from "@/lib/formatters";
import MetricChart from "./MetricChart";
import SignalChart from "./SignalChart";

interface BloodworkSectionProps {
  labs: LabResult[];
  phaseStartedAt?: string;
}

interface LabMetricGroup {
  loinc: string;
  name: string;
  category: string;
  unit: string;
  latest: LabResult;
  history: LabResult[];
  refLow: number;
  refHigh: number;
}

function groupLabsByMetric(labs: LabResult[]): LabMetricGroup[] {
  const groups: Record<string, LabMetricGroup> = {};
  for (const lab of labs) {
    const isLoinc = /^\d+-\d$/.test(lab.metric_name || "");
    const name = !lab.metric_name || isLoinc ? `Unknown (${lab.metric_loinc})` : lab.metric_name;
    if (!groups[lab.metric_loinc]) {
      groups[lab.metric_loinc] = { loinc: lab.metric_loinc, name, category: lab.category || "unknown", unit: lab.unit_canonical, latest: lab, history: [], refLow: lab.reference_low, refHigh: lab.reference_high };
    }
    groups[lab.metric_loinc].history.push(lab);
    if (lab.observation_date > groups[lab.metric_loinc].latest.observation_date) groups[lab.metric_loinc].latest = lab;
  }
  Object.values(groups).forEach((g) => g.history.sort((a, b) => a.observation_date.localeCompare(b.observation_date)));
  return Object.values(groups);
}

export default function BloodworkSection({ labs, phaseStartedAt }: BloodworkSectionProps) {
  const [expandedMetric, setExpandedMetric] = useState<string | null>(null);
  const [showRefRange, setShowRefRange] = useState(false);

  const metrics = groupLabsByMetric(labs);
  const byCategory: Record<string, LabMetricGroup[]> = {};
  metrics.forEach((m) => { if (!byCategory[m.category]) byCategory[m.category] = []; byCategory[m.category].push(m); });

  if (!metrics.length) return <p className="text-sm py-8 text-center" style={{ color: "var(--color-text-muted)" }}>No bloodwork uploaded yet.</p>;

  return (
    <div className="space-y-5">
      {Object.entries(byCategory).map(([category, catMetrics]) => (
        <div key={category}>
          <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--color-text-muted)" }}>{category}</p>
          <div className="rounded-xl border overflow-hidden" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)" }}>
            {catMetrics.map((m, i) => {
              const fc = getFlagColor(m.latest.flag);
              const isExp = expandedMetric === m.loinc;
              const chartData = m.history.map((h) => ({ date: h.observation_date, value: h.value_canonical }));
              return (
                <div key={m.loinc}>
                  {i > 0 && <div style={{ borderTop: "1px solid var(--color-border-card)" }} />}
                  <button onClick={() => setExpandedMetric(isExp ? null : m.loinc)} className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[var(--color-bg-secondary)] transition-colors">
                    <span className="text-sm font-medium flex-1" style={{ color: "var(--color-text-primary)" }}>{m.name}</span>
                    <span className="text-sm font-medium" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>{m.latest.value_canonical} {m.unit}</span>
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded capitalize" style={{ background: fc.bg, color: fc.text }}>{m.latest.flag}</span>
                    {chartData.length >= 2 && <SignalChart dataPoints={chartData} color={m.latest.flag === "high" ? "#C44536" : m.latest.flag === "low" ? "#C98B2F" : "#5A8A5C"} width={80} height={28} />}
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.5" strokeLinecap="round" style={{ transform: isExp ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.2s" }}><path d="M3 5l4 4 4-4" /></svg>
                  </button>
                  <AnimatePresence>
                    {isExp && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className="overflow-hidden">
                        <div className="px-4 pb-4 pt-1">
                          <div className="flex items-center gap-3 mb-3">
                            <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>{m.history.length} readings · {formatDateShort(m.history[0].observation_date)} – {formatDateShort(m.latest.observation_date)}</span>
                            <label className="flex items-center gap-1.5 text-xs cursor-pointer ml-auto" style={{ color: "var(--color-text-muted)" }}>
                              <input type="checkbox" checked={showRefRange} onChange={(e) => setShowRefRange(e.target.checked)} className="rounded" />Ref range
                            </label>
                          </div>
                          <MetricChart data={chartData} color={m.latest.flag === "high" ? "#C44536" : m.latest.flag === "low" ? "#C98B2F" : "#5A8A5C"} height={200} unit={m.unit} refLow={m.refLow} refHigh={m.refHigh} showRefRange={showRefRange} />
                          <div className="mt-3 text-xs" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
                            {m.history.map((h) => {
                              const hfc = getFlagColor(h.flag);
                              return (
                                <div key={h.observation_date} className="flex items-center gap-3 py-1 border-b" style={{ borderColor: "var(--color-border-card)" }}>
                                  <span style={{ color: "var(--color-text-muted)" }}>{formatDateShort(h.observation_date)}</span>
                                  <span style={{ color: "var(--color-text-primary)" }}>{h.value_canonical} {m.unit}</span>
                                  <span className="px-1 py-0.5 rounded text-[9px] capitalize" style={{ background: hfc.bg, color: hfc.text }}>{h.flag}</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
