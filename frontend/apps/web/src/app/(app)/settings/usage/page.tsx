"use client";

// Settings → Usage page (FE-8.6)

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { useLocale } from "@repo/ui/hooks";
import { useCredits } from "@/features/credits/hooks/useCredits";

export default function UsageSettingsPage() {
  const locale = useLocale();
  const { data, isPending } = useCredits();

  if (isPending) {
    return (
      <div className="p-6 space-y-4">
        <div className="h-8 w-48 rounded bg-muted animate-pulse" />
        <div className="h-32 rounded-xl bg-muted animate-pulse" />
      </div>
    );
  }

  if (!data) return null;

  const dateFormatter = new Intl.DateTimeFormat(
    locale === "IN" ? "en-IN" : "en-US",
    { month: "short", day: "numeric" },
  );

  const chartData = data.monthlyTrend.map((d) => ({
    date: dateFormatter.format(new Date(d.date)),
    credits: d.creditsConsumed,
  }));

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">Credit Usage</h1>

      {/* Daily credits remaining */}
      <section className="rounded-xl border border-border bg-card p-6">
        <h2 className="text-sm font-medium text-muted-foreground">
          Daily credits remaining
        </h2>
        <p
          aria-live="polite"
          aria-label={`${data.dailyCreditsRemaining} credits remaining today`}
          className="text-5xl font-mono font-bold mt-2 tabular-nums"
        >
          {data.dailyCreditsRemaining}
        </p>
        <p className="text-sm text-muted-foreground mt-1">
          of {data.dailyCreditsTotal} daily credits
        </p>
      </section>

      {/* Breakdown by feature */}
      <section className="rounded-xl border border-border bg-card p-6">
        <h2 className="text-lg font-semibold mb-4">Credits by feature</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-start py-2 font-medium text-muted-foreground">
                Feature
              </th>
              <th className="text-end py-2 font-medium text-muted-foreground">
                Credits used
              </th>
            </tr>
          </thead>
          <tbody>
            {data.breakdown.map(({ feature, creditsUsed }) => (
              <tr key={feature} className="border-b border-border/50">
                <td className="py-2">{feature}</td>
                <td className="py-2 text-end font-mono tabular-nums">
                  {creditsUsed}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Monthly cost trend */}
      <section className="rounded-xl border border-border bg-card p-6">
        <h2 className="text-lg font-semibold mb-4">Monthly trend</h2>
        <div
          aria-label="Monthly credit usage trend chart"
          role="img"
          className="h-48"
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={32}
              />
              <Tooltip
                formatter={(value: number) => [`${value}`, "Credits used"]}
              />
              <Line
                type="monotone"
                dataKey="credits"
                strokeWidth={2}
                dot={false}
                className="stroke-primary"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
