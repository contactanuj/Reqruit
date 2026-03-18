"use client";

// ApplicationStats.tsx — Funnel statistics for the application pipeline (FE-6.5)
// Uses recharts FunnelChart for visual representation (already in deps)

import {
  FunnelChart,
  Funnel,
  LabelList,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useApplicationStats } from "../hooks/useKanban";
import { KANBAN_COLUMNS } from "../types";
import type { ApplicationStatus } from "../types";

const STATUS_ORDER: ApplicationStatus[] = [
  "Saved",
  "Applied",
  "Interviewing",
  "Offered",
  "Accepted",
  "Rejected",
  "Withdrawn",
];

const STATUS_COLORS: Record<ApplicationStatus, string> = {
  Saved: "#94a3b8",
  Applied: "#3b82f6",
  Interviewing: "#f59e0b",
  Offered: "#22c55e",
  Accepted: "#10b981",
  Rejected: "#ef4444",
  Withdrawn: "#6b7280",
};

function SkeletonStats() {
  return (
    <div className="space-y-4" aria-hidden="true" data-testid="stats-skeleton">
      <div className="h-48 rounded-lg bg-muted animate-pulse" />
      <div className="h-32 rounded-lg bg-muted animate-pulse" />
    </div>
  );
}

export function ApplicationStats() {
  const { data: stats, isPending } = useApplicationStats();

  if (isPending) return <SkeletonStats />;

  if (!stats) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        Could not load statistics. Please try again later.
      </p>
    );
  }

  const total = stats.total;

  // Low-data state: fewer than 5 total applications
  if (total < 5) {
    return (
      <div className="space-y-4" data-testid="low-data-state">
        <p className="text-sm text-muted-foreground text-center py-4">
          Add more applications to see meaningful statistics
        </p>
        <ul className="flex flex-col gap-1" aria-label="Application counts by status">
          {STATUS_ORDER.map((status) => {
            const count = stats.by_status[status] ?? 0;
            return (
              <li key={status} className="flex items-center justify-between text-sm px-2 py-1.5 rounded-md bg-muted/30">
                <span>{status}</span>
                <span className="font-medium">{count}</span>
              </li>
            );
          })}
        </ul>
      </div>
    );
  }

  // Build funnel data (use main pipeline stages only — exclude terminal Rejected/Withdrawn from funnel)
  const funnelStages: ApplicationStatus[] = ["Saved", "Applied", "Interviewing", "Offered", "Accepted"];
  const funnelData = funnelStages.map((status, i, arr) => {
    const value = stats.by_status[status] ?? 0;
    const prevValue = i > 0 ? (stats.by_status[arr[i - 1]] ?? 0) : 0;
    return {
      name: KANBAN_COLUMNS.find((c) => c.status === status)?.label ?? status,
      value,
      fill: STATUS_COLORS[status],
      conversionRate:
        i > 0 && prevValue > 0
          ? ((value / prevValue) * 100).toFixed(1) + "%"
          : "\u2014",
    };
  });

  return (
    <div className="space-y-6" data-testid="application-stats">
      {/* Funnel chart */}
      <section aria-label="Application pipeline funnel chart">
        <h3 className="text-sm font-semibold mb-3">Pipeline Funnel</h3>
        <div
          role="img"
          aria-label={`Application pipeline funnel: ${funnelData.map((d) => `${d.name} ${d.value}`).join(", ")}`}
        >
          <ResponsiveContainer width="100%" height={240}>
            <FunnelChart>
              <Tooltip
                formatter={(value: number, name: string) => {
                  const item = funnelData.find((d) => d.name === name);
                  const rate = item?.conversionRate;
                  return [
                    rate && rate !== "\u2014" ? `${value} (${rate} conversion)` : value,
                    name,
                  ];
                }}
              />
              <Funnel dataKey="value" data={funnelData} isAnimationActive>
                <LabelList
                  position="right"
                  fill="#888"
                  stroke="none"
                  dataKey="name"
                />
              </Funnel>
            </FunnelChart>
          </ResponsiveContainer>
        </div>

        {/* Accessible text table as alternative to chart */}
        <table className="sr-only" aria-label="Pipeline funnel data table">
          <thead>
            <tr>
              <th>Stage</th>
              <th>Count</th>
              <th>Conversion</th>
            </tr>
          </thead>
          <tbody>
            {funnelData.map((row) => (
              <tr key={row.name}>
                <td>{row.name}</td>
                <td>{row.value}</td>
                <td>{row.conversionRate}</td>
              </tr>
            ))}
            {/* Terminal statuses */}
            <tr>
              <td>{KANBAN_COLUMNS.find((c) => c.status === "Rejected")?.label ?? "Rejected"}</td>
              <td>{stats.by_status["Rejected"] ?? 0}</td>
              <td>{"\u2014"}</td>
            </tr>
            <tr>
              <td>{KANBAN_COLUMNS.find((c) => c.status === "Withdrawn")?.label ?? "Withdrawn"}</td>
              <td>{stats.by_status["Withdrawn"] ?? 0}</td>
              <td>{"\u2014"}</td>
            </tr>
          </tbody>
        </table>
      </section>

      {/* Stage timing table */}
      <section aria-label="Average time per stage">
        <h3 className="text-sm font-semibold mb-3">Time in Stage</h3>
        <table
          className="w-full text-sm"
          aria-label="Stage timing: average days and total applications per status"
        >
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-1.5 font-medium text-muted-foreground">Stage</th>
              <th className="text-right py-1.5 font-medium text-muted-foreground">Avg Days</th>
              <th className="text-right py-1.5 font-medium text-muted-foreground">Total</th>
            </tr>
          </thead>
          <tbody>
            {STATUS_ORDER.map((status) => {
              const label = KANBAN_COLUMNS.find((c) => c.status === status)?.label ?? status;
              const avgDays = stats.avg_days_per_stage[status] ?? 0;
              const count = stats.by_status[status] ?? 0;
              return (
                <tr key={status} className="border-b border-border/50">
                  <td className="py-1.5">{label}</td>
                  <td className="text-right py-1.5 tabular-nums">
                    {avgDays.toFixed(1)}d
                  </td>
                  <td className="text-right py-1.5 tabular-nums">{count}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}
