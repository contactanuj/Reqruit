"use client";

// MarketPositionChart.tsx — FE-12.2: Market position visualization
// Uses recharts ComposedChart with bars for P25/P50/P75/P90 and ReferenceLine for user's offer.

import * as React from "react";
import { formatLPA } from "@repo/ui/lib/locale";
import { useLocale } from "@repo/ui/hooks";
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { MarketPosition } from "../types";

interface MarketPositionChartProps {
  marketPosition: MarketPosition;
  userTotal: number;
}

export function MarketPositionChart({
  marketPosition,
  userTotal,
}: MarketPositionChartProps) {
  const locale = useLocale();
  const { p25, p50, p75, p90, userPercentile, role, city } = marketPosition;

  const data = [
    { name: "P25", value: p25 },
    { name: "P50", value: p50 },
    { name: "P75", value: p75 },
    { name: "P90", value: p90 },
  ];

  const barColors = ["#94a3b8", "#60a5fa", "#34d399", "#f59e0b"];

  const percentileText = `Your offer is at the ${userPercentile}th percentile for ${role} in ${city}`;

  return (
    <div data-testid="market-position-chart" className="space-y-3">
      <h3 className="text-base font-semibold text-foreground">
        Market Position
      </h3>

      <p
        data-testid="percentile-summary"
        className="text-sm text-muted-foreground"
      >
        {percentileText}
      </p>

      <div
        aria-label={percentileText}
        role="img"
        className="h-[300px] w-full"
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis
              tick={{ fontSize: 12 }}
              tickFormatter={(v: number) => formatLPA(v, locale)}
            />
            <Tooltip
              formatter={(value: number) => [formatLPA(value, locale), "Salary"]}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {data.map((_entry, index) => (
                <Cell key={`cell-${index}`} fill={barColors[index]} />
              ))}
            </Bar>
            <ReferenceLine
              y={userTotal}
              stroke="#ef4444"
              strokeWidth={2}
              strokeDasharray="8 4"
              label={{
                value: `Your offer: ${formatLPA(userTotal, locale)}`,
                position: "insideTopRight",
                fill: "#ef4444",
                fontSize: 12,
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Percentile badge */}
      <div
        data-testid="percentile-badge"
        className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1"
      >
        <span className="text-xs text-muted-foreground">Your percentile:</span>
        <span
          className={`text-sm font-bold ${
            userPercentile >= 75
              ? "text-green-600 dark:text-green-400"
              : userPercentile >= 50
                ? "text-amber-600 dark:text-amber-400"
                : "text-red-600 dark:text-red-400"
          }`}
        >
          P{userPercentile}
        </span>
      </div>
    </div>
  );
}
