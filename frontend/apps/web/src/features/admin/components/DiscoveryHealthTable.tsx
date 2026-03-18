"use client";

// DiscoveryHealthTable.tsx — FE-15.2: Discovery source health table with sync

import { useDiscoverySourcesQuery, useSyncSource } from "../hooks/useDiscoverySources";
import { formatDate } from "@repo/ui/lib/locale";
import { useLocale } from "@repo/ui/hooks";

const STATUS_STYLES: Record<string, string> = {
  healthy: "bg-green-100 text-green-800",
  degraded: "bg-yellow-100 text-yellow-800",
  failed: "bg-red-100 text-red-800",
};

const STATUS_LABELS: Record<string, string> = {
  healthy: "Healthy",
  degraded: "Degraded",
  failed: "Failed",
};

export function DiscoveryHealthTable() {
  const locale = useLocale();
  const { data: sources, isLoading, isError } = useDiscoverySourcesQuery();
  const syncMutation = useSyncSource();

  if (isLoading) {
    return (
      <div data-testid="discovery-health-skeleton" className="animate-pulse space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 rounded bg-gray-200" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div data-testid="discovery-health-error" className="rounded border border-red-300 bg-red-50 p-4 text-red-700">
        Failed to load discovery sources.
      </div>
    );
  }

  return (
    <div data-testid="discovery-health-table" className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Source</th>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Status</th>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Last Sync</th>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {sources?.map((source) => (
            <tr key={source.id} data-testid={`source-row-${source.id}`}>
              <td className="px-4 py-2 text-sm font-medium">{source.name}</td>
              <td className="px-4 py-2">
                <span
                  data-testid={`status-badge-${source.id}`}
                  className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[source.status] ?? "bg-gray-100 text-gray-800"}`}
                >
                  {STATUS_LABELS[source.status] ?? source.status}
                </span>
              </td>
              <td className="px-4 py-2 text-sm text-gray-600">
                {formatDate(source.lastSyncTime, locale)}
              </td>
              <td className="px-4 py-2">
                <button
                  data-testid={`sync-button-${source.id}`}
                  onClick={() => syncMutation.mutate({ id: source.id })}
                  disabled={syncMutation.isPending && syncMutation.variables?.id === source.id}
                  className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {syncMutation.isPending && syncMutation.variables?.id === source.id
                    ? "Syncing..."
                    : "Sync now"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
