"use client";

// CostAnalyticsDashboard.tsx — FE-15.5: Cost analytics with trend chart and breakdowns

import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useCostAnalyticsQuery, useUserCostDetail } from "../hooks/useCostAnalytics";
import { CostBreakdownTable } from "./CostBreakdownTable";
import { formatDate } from "@repo/ui/lib/locale";
import { useLocale } from "@repo/ui/hooks";

export function CostAnalyticsDashboard() {
  const locale = useLocale();
  const { data: analytics, isLoading, isError } = useCostAnalyticsQuery();
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  // User cost detail is fetched when a user row is clicked
  const { data: userCostDetail } = useUserCostDetail(selectedUserId);

  if (isLoading) {
    return (
      <div data-testid="cost-dashboard-skeleton" className="animate-pulse space-y-4">
        <div className="h-24 rounded bg-gray-200" />
        <div className="h-64 rounded bg-gray-200" />
        <div className="h-48 rounded bg-gray-200" />
      </div>
    );
  }

  if (isError) {
    return (
      <div data-testid="cost-dashboard-error" className="rounded border border-red-300 bg-red-50 p-4 text-red-700">
        Failed to load cost analytics.
      </div>
    );
  }

  if (!analytics) return null;

  return (
    <div data-testid="cost-dashboard" className="space-y-6">
      {/* Total spend card */}
      <div
        data-testid="total-spend"
        className="rounded-lg border bg-white p-6 shadow-sm"
      >
        <h3 className="text-sm font-medium text-gray-500">Total Spend</h3>
        <p className="mt-1 text-3xl font-bold text-gray-900">
          {locale === "IN"
            ? `\u20B9${analytics.totalSpend.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : `$${analytics.totalSpend.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
        </p>
      </div>

      {/* Daily cost trend chart */}
      <div
        data-testid="cost-trend-chart"
        className="rounded-lg border bg-white p-6 shadow-sm"
        role="img"
        aria-label="Daily cost trend chart showing spending over time"
      >
        <h3 className="mb-4 text-sm font-medium text-gray-500">Daily Cost Trend</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={analytics.dailyTrend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="cost"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Breakdown tables */}
      <div className="grid gap-6 md:grid-cols-2">
        <div data-testid="top-users-table">
          <CostBreakdownTable
            entries={analytics.topUsersByCost}
            label="Top Users by Cost"
            onRowClick={(id) => setSelectedUserId(id)}
          />
        </div>
        <div data-testid="top-agents-table">
          <CostBreakdownTable
            entries={analytics.topAgentsByCost}
            label="Top Agents by Cost"
          />
        </div>
      </div>

      {/* User cost detail panel */}
      {selectedUserId && (
        <div
          data-testid="user-cost-detail-panel"
          className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l bg-white shadow-xl"
          role="dialog"
          aria-label={`Cost details for user ${selectedUserId}`}
        >
          <div className="flex items-center justify-between border-b px-4 py-3">
            <h3 className="text-sm font-semibold text-gray-900">
              User Cost Detail
            </h3>
            <button
              type="button"
              data-testid="close-user-detail"
              onClick={() => setSelectedUserId(null)}
              aria-label="Close detail panel"
              className="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
            >
              &times;
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {!userCostDetail ? (
              <div className="flex items-center justify-center py-12 text-sm text-gray-500">
                Loading user cost details...
              </div>
            ) : (
              <div className="space-y-4">
                <p className="text-sm text-gray-600">
                  User ID: <span className="font-mono">{userCostDetail.userId}</span>
                </p>
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-gray-500">
                        Date
                      </th>
                      <th scope="col" className="px-3 py-2 text-right text-xs font-medium text-gray-500">
                        Cost
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {userCostDetail.dailyCosts.map((entry) => (
                      <tr key={entry.date}>
                        <td className="px-3 py-2 text-sm">{formatDate(entry.date, locale)}</td>
                        <td className="px-3 py-2 text-right text-sm tabular-nums">
                          {locale === "IN"
                            ? `\u20B9${entry.cost.toFixed(2)}`
                            : `$${entry.cost.toFixed(2)}`}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
