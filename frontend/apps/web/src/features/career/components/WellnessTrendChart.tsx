"use client";

// WellnessTrendChart — FE-13.2
// Line chart showing mood and energy trends over the past 30 days.

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import type { WellnessTrend } from "../types";

interface WellnessTrendChartProps {
  trend: WellnessTrend;
}

function formatShortDate(dateStr: string): string {
  try {
    return new Intl.DateTimeFormat("en-US", {
      day: "2-digit",
      month: "short",
    }).format(new Date(dateStr));
  } catch {
    return dateStr.substring(5);
  }
}

export function WellnessTrendChart({ trend }: WellnessTrendChartProps) {
  const chartData = trend.data.slice(-30).map((d) => ({
    ...d,
    label: formatShortDate(d.date),
  }));

  return (
    <div
      data-testid="wellness-trend-chart"
      aria-label="Wellness trend chart for the past 30 days"
      role="img"
      className="w-full h-48"
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[1, 5]}
            ticks={[1, 2, 3, 4, 5]}
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={24}
          />
          <Tooltip
            formatter={(value: number, name: string) => [
              value,
              name === "mood" ? "Mood" : "Energy",
            ]}
            labelFormatter={(label: string) => label}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="mood"
            name="Mood"
            strokeWidth={2}
            dot={false}
            stroke="#8b5cf6"
          />
          <Line
            type="monotone"
            dataKey="energy"
            name="Energy"
            strokeWidth={2}
            dot={false}
            stroke="#f59e0b"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
