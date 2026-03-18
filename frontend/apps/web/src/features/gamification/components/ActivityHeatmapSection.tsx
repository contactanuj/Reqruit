"use client";

// ActivityHeatmapSection — Dashboard activity tab (FE-8.3)
// Combines ActivityHeatmap and XPTrendChart.

import { ActivityHeatmap } from "./ActivityHeatmap";
import { XPTrendChart } from "./XPTrendChart";
import { useActivityHistory } from "../hooks/useGamification";

export function ActivityHeatmapSection() {
  const { data, isPending } = useActivityHistory();

  if (isPending) {
    return (
      <div className="space-y-4">
        <div className="h-32 rounded-lg bg-muted animate-pulse motion-reduce:animate-none" />
        <div className="h-48 rounded-lg bg-muted animate-pulse motion-reduce:animate-none" />
      </div>
    );
  }

  if (!data) return null;

  return (
    <section className="space-y-6">
      <div className="rounded-xl border border-border bg-card p-4 space-y-3">
        <h2 className="text-lg font-semibold">Activity</h2>
        <ActivityHeatmap days={data.days} />
      </div>

      <div className="rounded-xl border border-border bg-card p-4 space-y-3">
        <h2 className="text-lg font-semibold">XP Trend (last 30 days)</h2>
        <XPTrendChart days={data.days} />
      </div>
    </section>
  );
}
