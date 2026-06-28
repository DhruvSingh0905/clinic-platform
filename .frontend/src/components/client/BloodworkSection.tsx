"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { LabResult } from "@/lib/types";
import { getFlagColor, formatDateShort } from "@/lib/formatters";
import MetricChart from "./MetricChart";
import SignalChart from "./SignalChart";

interface BloodworkSectionProps {
  labs: LabResult[];
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

export default function BloodworkSection({ labs }: BloodworkSectionProps) {
  const [expandedMetric, setExpandedMetric] = useState<string | null>(null);
  const [showRefRange, setShowRefRange] = useState(false);
  const [search, setSearch] = useState("");

  const allMetrics = groupLabsByMetric(labs);
  const metrics = search
    ? allMetrics.filter((m) => m.name.toLowerCase().includes(search.toLowerCase()))
    : allMetrics;
  const byCategory: Record<string, LabMetricGroup[]> = {};
  metrics.forEach((m) => { if (!byCategory[m.category]) byCategory[m.category] = []; byCategory[m.category].push(m); });

  if (!allMetrics.length) return <p className="text-xs py-6 text-center" style={{ color: "var(--color-text-muted)" }}>No bloodwork uploaded yet.</p>;

  return (
    <div className="space-y-4">
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search tests..."
        className="text-xs px-3 py-1.5 w-full border"
        style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-input)", color: "var(--color-text-primary)", borderRadius: "3px" }}
      />
      {Object.entries(byCategory).map(([category, catMetrics]) => (
        <div key={category}>
          <p className="text-[10px] font-semibold uppercase tracking-wider mb-1.5" style={{ color: "var(--color-text-muted)" }}>{category}</p>
          <div className="border overflow-hidden" style={{ borderColor: "var(--color-border-light)", background: "var(--color-bg-card)", borderRadius: "3px" }}>
            {catMetrics.map((m, i) => {
              const fc = getFlagColor(m.latest.flag);
              const isExp = expandedMetric === m.loinc;
              const chartData = m.history.map((h) => ({ date: h.observation_date, value: h.value_canonical }));
              return (
                <div key={m.loinc}>
                  {i > 0 && <div style={{ borderTop: "1px solid var(--color-border-light)" }} />}
                  <button onClick={() => setExpandedMetric(isExp ? null : m.loinc)} className="w-full flex items-center gap-3 px-3 py-2 text-left data-row transition-colors" style={{ background: isExp ? "var(--color-bg-hover)" : "transparent" }}>
                    <span className="text-xs font-medium flex-1" style={{ color: "var(--color-text-primary)" }}>{m.name}</span>
                    <span className="text-xs" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-secondary)" }}>{m.latest.value_canonical} {m.unit}</span>
                    <span className="text-[9px] font-medium px-1.5 py-0.5 capitalize" style={{ background: fc.bg, color: fc.text, borderRadius: "2px" }}>{m.latest.flag}</span>
                    {chartData.length >= 2 && <SignalChart dataPoints={chartData} color={m.latest.flag === "high" ? "#E5534B" : m.latest.flag === "low" ? "#D4952A" : "#3FB950"} width={64} height={24} />}
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="var(--color-text-muted)" strokeWidth="1.5" strokeLinecap="round" style={{ transform: isExp ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.15s" }}><path d="M2 3.5l3 3 3-3" /></svg>
                  </button>
                  <AnimatePresence>
                    {isExp && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.15 }} className="overflow-hidden">
                        <div className="px-3 pb-3 pt-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-[10px]" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-muted)" }}>{m.history.length} readings · {formatDateShort(m.history[0].observation_date)} – {formatDateShort(m.latest.observation_date)}</span>
                            <label className="flex items-center gap-1 text-[10px] cursor-pointer ml-auto" style={{ color: "var(--color-text-muted)" }}>
                              <input type="checkbox" checked={showRefRange} onChange={(e) => setShowRefRange(e.target.checked)} />Ref range
                            </label>
                          </div>
                          <MetricChart data={chartData} color={m.latest.flag === "high" ? "#E5534B" : m.latest.flag === "low" ? "#D4952A" : "#3FB950"} height={160} unit={m.unit} refLow={m.refLow} refHigh={m.refHigh} showRefRange={showRefRange} />
                          <div className="mt-2" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
                            {m.history.map((h) => {
                              const hfc = getFlagColor(h.flag);
                              return (
                                <div key={h.observation_date} className="flex items-center gap-3 py-1 text-[11px] border-b" style={{ borderColor: "var(--color-border-light)" }}>
                                  <span style={{ color: "var(--color-text-muted)" }}>{formatDateShort(h.observation_date)}</span>
                                  <span style={{ color: "var(--color-text-primary)" }}>{h.value_canonical} {m.unit}</span>
                                  <span className="text-[9px] px-1 py-0.5 capitalize" style={{ background: hfc.bg, color: hfc.text, borderRadius: "2px" }}>{h.flag}</span>
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
