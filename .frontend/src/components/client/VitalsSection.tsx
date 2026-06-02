"use client";

import type { WearableMetric } from "@/lib/types";
import { WEARABLE_META, formatMetric } from "@/lib/formatters";
import MetricChart from "./MetricChart";

interface VitalsSectionProps {
  wearables: WearableMetric[];
}

export default function VitalsSection({ wearables }: VitalsSectionProps) {
  const byMetric: Record<string, { latest: WearableMetric; history: { date: string; value: number }[] }> = {};
  const sorted = [...wearables].sort((a, b) => a.observation_date.localeCompare(b.observation_date));
  for (const w of sorted) {
    if (!byMetric[w.metric]) byMetric[w.metric] = { latest: w, history: [] };
    byMetric[w.metric].history.push({ date: w.observation_date, value: w.value_mean });
    if (w.observation_date >= byMetric[w.metric].latest.observation_date) byMetric[w.metric].latest = w;
  }

  const metrics = Object.entries(byMetric)
    .map(([key, data]) => ({ key, ...data, meta: WEARABLE_META[key] || { label: key, color: "#9B948D", priority: 99 } }))
    .sort((a, b) => a.meta.priority - b.meta.priority);

  function computeTrend(history: { date: string; value: number }[]): { delta: number; pct: number; direction: string } | null {
    if (history.length < 2) return null;
    const first = history[0].value;
    const last = history[history.length - 1].value;
    const delta = Math.round((last - first) * 10) / 10;
    const pct = first > 0 ? Math.round((last - first) / first * 1000) / 10 : 0;
    return { delta, pct, direction: delta > 0 ? "↑" : delta < 0 ? "↓" : "→" };
  }

  const weight = metrics.find((m) => m.key === "weight_kg" || m.key === "weight");
  const others = metrics.filter((m) => m.key !== "weight_kg" && m.key !== "weight" && m.meta.priority < 10);
  const demoted = metrics.filter((m) => m.meta.priority >= 10);

  return (
    <div className="space-y-4">
      {weight && (
        <div className="rounded-xl p-5 border" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)", boxShadow: "var(--shadow-card)" }}>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider" style={{ color: weight.meta.color }}>{weight.meta.label}</span>
            <span className="ml-auto text-xs" style={{ color: "var(--color-text-muted)" }}>{weight.latest.source}</span>
          </div>
          <div className="flex items-baseline gap-3">
            <p className="text-3xl font-medium" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-primary)" }}>
              {formatMetric(weight.latest.value_mean, weight.latest.unit)}
            </p>
            {(() => {
              const trend = computeTrend(weight.history);
              if (!trend) return null;
              const color = trend.delta > 0 ? "#C98B2F" : trend.delta < 0 ? "#4A7FA5" : "var(--color-text-muted)";
              return (
                <span className="text-sm font-medium" style={{ color }}>
                  {trend.direction} {trend.delta > 0 ? "+" : ""}{trend.delta}{weight.latest.unit} ({trend.pct > 0 ? "+" : ""}{trend.pct}%)
                </span>
              );
            })()}
          </div>
          <div className="mt-3"><MetricChart data={weight.history} color={weight.meta.color} height={200} unit={weight.latest.unit} /></div>
        </div>
      )}
      <div className="grid grid-cols-2 gap-4">
        {others.map((m) => (
          <div key={m.key} className="rounded-xl p-4 border" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-card)", boxShadow: "var(--shadow-card)" }}>
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-xs font-medium" style={{ color: "var(--color-text-muted)" }}>{m.meta.label}</span>
              <span className="ml-auto text-[10px]" style={{ color: "var(--color-text-muted)" }}>{m.latest.source}</span>
            </div>
            <p className="text-xl font-medium mb-2" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>{formatMetric(m.latest.value_mean, m.latest.unit)}</p>
            <MetricChart data={m.history} color={m.meta.color} height={120} unit={m.latest.unit} />
          </div>
        ))}
      </div>
      {demoted.length > 0 && (
        <div className="flex gap-3">
          {demoted.map((m) => (
            <div key={m.key} className="rounded-lg px-3 py-2 border flex items-center gap-3" style={{ borderColor: "var(--color-border-card)", background: "var(--color-bg-secondary)" }}>
              <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>{m.meta.label}</span>
              <span className="text-sm" style={{ fontFamily: "'IBM Plex Mono', monospace", color: "var(--color-text-secondary)" }}>{formatMetric(m.latest.value_mean, m.latest.unit)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
