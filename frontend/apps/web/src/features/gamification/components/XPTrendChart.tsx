"use client";

// XPTrendChart — FE-8.3
// Line chart showing XP earned per day for the past 30 days.

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { ActivityDay } from "../hooks/useGamification";

interface XPTrendChartProps {
  days: ActivityDay[];
  locale?: string;
}

function formatShortDate(dateStr: string, locale: string): string {
  try {
    return new Intl.DateTimeFormat(locale, {
      day: "2-digit",
      month: "short",
    }).format(new Date(dateStr));
  } catch {
    return dateStr.substring(5); // MM-DD fallback
  }
}

export function XPTrendChart({ days, locale = "en-IN" }: XPTrendChartProps) {
  // Take last 30 days
  const last30 = days.slice(-30);

  const chartData = last30.map((d) => ({
    date: d.date,
    xp: d.xpEarned,
    label: formatShortDate(d.date, locale),
  }));

  return (
    <div
      aria-label="XP trend chart for the past 30 days"
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
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={36}
          />
          <Tooltip
            formatter={(value: number) => [`${value} XP`, "XP earned"]}
            labelFormatter={(label: string) => label}
          />
          <Line
            type="monotone"
            dataKey="xp"
            strokeWidth={2}
            dot={false}
            className="stroke-primary"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
