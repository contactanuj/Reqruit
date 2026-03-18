"use client";

// BurnoutGauge — FE-13.2
// Semi-circular gauge displaying burnout risk score using recharts RadialBarChart.

import {
  RadialBarChart,
  RadialBar,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";

interface BurnoutGaugeProps {
  score: number; // 0-100
  trend?: { date: string; score: number }[];
}

function getScoreColor(score: number): string {
  if (score <= 30) return "#22c55e"; // green
  if (score <= 60) return "#f59e0b"; // amber
  return "#ef4444"; // red
}

function getScoreLabel(score: number): string {
  if (score <= 30) return "Low";
  if (score <= 60) return "Moderate";
  return "High";
}

export function BurnoutGauge({ score, trend }: BurnoutGaugeProps) {
  const color = getScoreColor(score);
  const label = getScoreLabel(score);
  const clampedScore = Math.max(0, Math.min(100, score));

  const data = [
    {
      name: "burnout",
      value: clampedScore,
      fill: color,
    },
  ];

  return (
    <div data-testid="burnout-gauge" className="relative w-full" style={{ height: 160 }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          cx="50%"
          cy="100%"
          innerRadius="60%"
          outerRadius="90%"
          startAngle={180}
          endAngle={0}
          barSize={16}
          data={data}
        >
          <RadialBar
            dataKey="value"
            cornerRadius={8}
            background={{ fill: "#e5e7eb" }}
          />
        </RadialBarChart>
      </ResponsiveContainer>

      <div
        className="absolute inset-0 flex flex-col items-center justify-end pb-2"
        data-testid="burnout-score"
      >
        <span className="text-2xl font-bold" style={{ color }}>
          {clampedScore}
        </span>
        <span className="text-xs text-muted-foreground">{label} risk</span>
      </div>

      {/* 7-day trend sparkline */}
      {trend && trend.length > 1 && (
        <div
          data-testid="burnout-trend"
          className="mt-2 h-10 w-full"
          aria-label="7-day burnout trend"
          role="img"
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trend.slice(-7)}>
              <Line
                type="monotone"
                dataKey="score"
                stroke={color}
                strokeWidth={1.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
