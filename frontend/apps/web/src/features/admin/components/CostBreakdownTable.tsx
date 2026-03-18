"use client";

// CostBreakdownTable.tsx — FE-15.5: Cost breakdown with anomaly indicators

import { useLocale } from "@repo/ui/hooks";
import type { CostEntry } from "../types";

interface CostBreakdownTableProps {
  entries: CostEntry[];
  label: string;
  onRowClick?: (id: string) => void;
}

export function CostBreakdownTable({ entries, label, onRowClick }: CostBreakdownTableProps) {
  const locale = useLocale();
  const fmtCost = (amount: number) =>
    locale === "IN"
      ? `\u20B9${amount.toFixed(2)}`
      : `$${amount.toFixed(2)}`;

  return (
    <div data-testid="cost-breakdown-table" className="overflow-x-auto">
      <h3 className="mb-2 text-sm font-semibold text-gray-700">{label}</h3>
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Name</th>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Total Cost</th>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {entries.map((entry) => (
            <tr
              key={entry.id}
              data-testid={`cost-row-${entry.id}`}
              onClick={() => onRowClick?.(entry.id)}
              className={onRowClick ? "cursor-pointer hover:bg-gray-50" : ""}
            >
              <td className="px-4 py-2 text-sm font-medium">{entry.name}</td>
              <td className="px-4 py-2 text-sm">{fmtCost(entry.totalCost)}</td>
              <td className="px-4 py-2">
                {entry.isAnomaly && (
                  <span
                    data-testid={`anomaly-indicator-${entry.id}`}
                    className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800"
                  >
                    <svg
                      className="h-3 w-3"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z"
                        clipRule="evenodd"
                      />
                    </svg>
                    Anomaly detected
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
