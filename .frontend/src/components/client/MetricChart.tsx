"use client";

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Brush } from "recharts";
import { formatDateShort } from "@/lib/formatters";

interface MetricChartProps {
  data: { date: string; value: number }[];
  color: string;
  height?: number;
  unit?: string;
  showBrush?: boolean;
  refLow?: number;
  refHigh?: number;
  showRefRange?: boolean;
}

let _chartId = 0;

export default function MetricChart({ data, color, height = 120, unit = "", refLow, refHigh, showRefRange = false, showBrush = false }: MetricChartProps) {
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
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.15} />
            <stop offset="95%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="date"
          tick={{ fontSize: 10, fill: "var(--color-text-muted)", fontFamily: "'IBM Plex Mono', monospace" }}
          tickFormatter={(d) => formatDateShort(d)}
          tickLine={false}
          axisLine={{ stroke: "var(--color-border-light)" }}
          interval="preserveStartEnd"
        />
        <YAxis
          domain={[min - padding, max + padding]}
          tick={{ fontSize: 10, fill: "var(--color-text-muted)", fontFamily: "'IBM Plex Mono', monospace" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => `${Math.round(v * 10) / 10}`}
          width={45}
        />
        <Tooltip
          contentStyle={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border-emphasis)",
            borderRadius: "3px",
            fontSize: "11px",
            fontFamily: "'IBM Plex Mono', monospace",
            color: "var(--color-text-primary)",
          }}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter={(value: any) => [`${Math.round(Number(value) * 10) / 10} ${unit}`, ""]}
          labelFormatter={(label) => formatDateShort(label as string)}
        />
        {showRefRange && refLow != null && refHigh != null && (
          <>
            <ReferenceLine y={refLow} stroke="#3FB950" strokeWidth={1} strokeDasharray="4 3" label={{ value: `${refLow}`, position: "insideBottomLeft", fontSize: 9, fill: "#3FB950", fontFamily: "'IBM Plex Mono', monospace" }} />
            <ReferenceLine y={refHigh} stroke="#3FB950" strokeWidth={1} strokeDasharray="4 3" label={{ value: `${refHigh}`, position: "insideTopLeft", fontSize: 9, fill: "#3FB950", fontFamily: "'IBM Plex Mono', monospace" }} />
          </>
        )}
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#${gradId})`}
          dot={false}
          activeDot={{ r: 3, fill: color, stroke: "var(--color-bg-card)", strokeWidth: 2 }}
        />
        {showBrush && data.length > 4 && (
          <Brush
            dataKey="date"
            height={20}
            stroke="var(--color-border-emphasis)"
            fill="var(--color-bg-secondary)"
            tickFormatter={(d) => formatDateShort(d)}
            travellerWidth={8}
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  );
}
