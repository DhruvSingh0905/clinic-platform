"use client";

import { LineChart, Line, ResponsiveContainer, Tooltip } from "recharts";
import { formatDateShort } from "@/lib/formatters";

interface SignalChartProps {
  dataPoints: { date: string; value: number }[];
  color: string;
  width?: number;
  height?: number;
}

export default function SignalChart({ dataPoints, color, width = 100, height = 32 }: SignalChartProps) {
  if (dataPoints.length < 2) return null;

  return (
    <div style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={dataPoints} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Tooltip
            contentStyle={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border-emphasis)",
              borderRadius: "3px",
              fontSize: "10px",
              fontFamily: "'IBM Plex Mono', monospace",
              padding: "3px 6px",
              color: "var(--color-text-primary)",
            }}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(v: any) => [`${Math.round(Number(v) * 10) / 10}`, ""]}
            labelFormatter={(l) => formatDateShort(l as string)}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 2.5, fill: color, stroke: "var(--color-bg-card)", strokeWidth: 1.5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
