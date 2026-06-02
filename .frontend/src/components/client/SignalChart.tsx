"use client";

import { LineChart, Line, ResponsiveContainer, Tooltip } from "recharts";
import { formatDateShort } from "@/lib/formatters";

interface SignalChartProps {
  dataPoints: { date: string; value: number }[];
  color: string;
  width?: number;
  height?: number;
}

/** Dynamic mini-chart for any signal data. Works with any data shape. */
export default function SignalChart({ dataPoints, color, width = 120, height = 48 }: SignalChartProps) {
  if (dataPoints.length < 2) return null;

  return (
    <div style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={dataPoints} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Tooltip
            contentStyle={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border-card)",
              borderRadius: "6px",
              fontSize: "10px",
              fontFamily: "'IBM Plex Mono', monospace",
              padding: "4px 8px",
            }}
            formatter={(v: number) => [`${Math.round(v * 10) / 10}`, ""]}
            labelFormatter={(l) => formatDateShort(l as string)}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3, fill: color, stroke: "white", strokeWidth: 1.5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
