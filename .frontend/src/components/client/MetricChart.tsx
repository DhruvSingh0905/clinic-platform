"use client";

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { formatDateShort } from "@/lib/formatters";

interface MetricChartProps {
  data: { date: string; value: number }[];
  color: string;
  height?: number;
  unit?: string;
  refLow?: number;
  refHigh?: number;
  showRefRange?: boolean;
}

let _chartId = 0;

export default function MetricChart({ data, color, height = 120, unit = "", refLow, refHigh, showRefRange = false }: MetricChartProps) {
  const gradId = `mc-${++_chartId}`;
  if (!data.length) return <div className="text-xs" style={{ color: "var(--color-text-muted)" }}>No data</div>;

  const values = data.map((d) => d.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padding = (max - min) * 0.15 || max * 0.1 || 1;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
        <defs>
          <linearGradient id={`${gradId}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.2} />
            <stop offset="95%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
          tickFormatter={(d) => formatDateShort(d)}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          domain={[min - padding, max + padding]}
          tick={{ fontSize: 10, fill: "var(--color-text-muted)" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => {
            const rounded = Math.round(v * 10) / 10;
            return rounded % 1 === 0 ? `${rounded}` : `${rounded}`;
          }}
          width={45}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border-card)",
            borderRadius: "8px",
            boxShadow: "var(--shadow-elevated)",
            fontSize: "12px",
            fontFamily: "'IBM Plex Mono', monospace",
          }}
          formatter={(value: number) => [`${Math.round(value * 10) / 10} ${unit}`, ""]}
          labelFormatter={(label) => formatDateShort(label as string)}
        />
        {showRefRange && refLow != null && refHigh != null && (
          <>
            <ReferenceLine y={refLow} stroke="#5A8A5C" strokeWidth={2} strokeDasharray="6 3" label={{ value: `Low: ${refLow}`, position: "insideBottomLeft", fontSize: 10, fontWeight: 600, fill: "#5A8A5C" }} />
            <ReferenceLine y={refHigh} stroke="#5A8A5C" strokeWidth={2} strokeDasharray="6 3" label={{ value: `High: ${refHigh}`, position: "insideTopLeft", fontSize: 10, fontWeight: 600, fill: "#5A8A5C" }} />
          </>
        )}
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          fill={`url(#${gradId})`}
          dot={false}
          activeDot={{ r: 4, fill: color, stroke: "white", strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
