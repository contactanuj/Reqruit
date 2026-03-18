"use client";

// PiiEventsTable.tsx — FE-15.4: PII events review table with two-section layout

import DOMPurify from "dompurify";
import { usePiiEventsQuery, useResolvePiiEvent } from "../hooks/usePiiEvents";
import { formatDate } from "@repo/ui/lib/locale";
import { useLocale } from "@repo/ui/hooks";
import type { LocaleCode } from "@repo/ui/lib/locale";
import type { PiiEvent } from "../types";

function sanitizeAndTruncate(content: string, maxLength = 100): string {
  const sanitized = DOMPurify.sanitize(content, { ALLOWED_TAGS: [] });
  return sanitized.length > maxLength
    ? sanitized.slice(0, maxLength) + "..."
    : sanitized;
}

function PiiEventRow({
  event,
  onConfirm,
  onMarkFalsePositive,
  isPending,
  locale,
}: {
  event: PiiEvent;
  onConfirm: (id: string) => void;
  onMarkFalsePositive: (id: string) => void;
  isPending: boolean;
  locale: LocaleCode;
}) {
  return (
    <tr data-testid={`pii-event-${event.id}`}>
      <td className="px-4 py-2 text-sm font-mono">{event.id}</td>
      <td className="px-4 py-2 text-sm text-gray-600">
        {formatDate(event.timestamp, locale)}
      </td>
      <td className="px-4 py-2 text-sm">{event.eventType}</td>
      <td className="px-4 py-2 text-sm text-gray-700">
        {sanitizeAndTruncate(event.contentSnippet)}
      </td>
      <td className="px-4 py-2 text-sm">{event.userId}</td>
      <td className="px-4 py-2">
        <span
          className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
            event.status === "pending"
              ? "bg-yellow-100 text-yellow-800"
              : event.status === "confirmed"
                ? "bg-red-100 text-red-800"
                : "bg-gray-100 text-gray-800"
          }`}
        >
          {event.status}
        </span>
      </td>
      <td className="flex gap-2 px-4 py-2">
        {event.status === "pending" && (
          <>
            <button
              data-testid={`confirm-pii-${event.id}`}
              onClick={() => onConfirm(event.id)}
              disabled={isPending}
              className="rounded bg-red-600 px-2 py-1 text-xs text-white hover:bg-red-700 disabled:opacity-50"
            >
              Confirm PII
            </button>
            <button
              data-testid={`mark-false-positive-${event.id}`}
              onClick={() => onMarkFalsePositive(event.id)}
              disabled={isPending}
              className="rounded border px-2 py-1 text-xs hover:bg-gray-100 disabled:opacity-50"
            >
              Mark false positive
            </button>
          </>
        )}
      </td>
    </tr>
  );
}

export function PiiEventsTable() {
  const { data: events, isLoading, isError } = usePiiEventsQuery();
  const resolveMutation = useResolvePiiEvent();
  const locale = useLocale();

  const pendingEvents = events?.filter((e) => e.status === "pending") ?? [];
  const resolvedEvents = events?.filter((e) => e.status !== "pending") ?? [];

  const handleConfirm = (id: string) => {
    resolveMutation.mutate({ id, status: "confirmed" });
  };

  const handleMarkFalsePositive = (id: string) => {
    resolveMutation.mutate({ id, status: "false_positive" });
  };

  if (isLoading) {
    return (
      <div data-testid="pii-events-skeleton" className="animate-pulse space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 rounded bg-gray-200" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div data-testid="pii-events-error" className="rounded border border-red-300 bg-red-50 p-4 text-red-700">
        Failed to load PII events.
      </div>
    );
  }

  const tableHead = (
    <thead className="bg-gray-50">
      <tr>
        <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">ID</th>
        <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Timestamp</th>
        <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Event Type</th>
        <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Content</th>
        <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">User</th>
        <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Status</th>
        <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Actions</th>
      </tr>
    </thead>
  );

  return (
    <div data-testid="pii-events-table" className="space-y-6">
      {/* Pending events section */}
      <section data-testid="pending-section">
        <h3 className="mb-2 text-lg font-semibold text-yellow-800">
          Pending Review ({pendingEvents.length})
        </h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            {tableHead}
            <tbody className="divide-y divide-gray-200">
              {pendingEvents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-4 text-center text-sm text-gray-500">
                    No pending events.
                  </td>
                </tr>
              ) : (
                pendingEvents.map((event) => (
                  <PiiEventRow
                    key={event.id}
                    event={event}
                    onConfirm={handleConfirm}
                    onMarkFalsePositive={handleMarkFalsePositive}
                    isPending={resolveMutation.isPending}
                    locale={locale}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Resolved events section */}
      <section data-testid="resolved-section">
        <h3 className="mb-2 text-lg font-semibold text-gray-600">
          Resolved ({resolvedEvents.length})
        </h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            {tableHead}
            <tbody className="divide-y divide-gray-200">
              {resolvedEvents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-4 text-center text-sm text-gray-500">
                    No resolved events.
                  </td>
                </tr>
              ) : (
                resolvedEvents.map((event) => (
                  <PiiEventRow
                    key={event.id}
                    event={event}
                    onConfirm={handleConfirm}
                    onMarkFalsePositive={handleMarkFalsePositive}
                    isPending={resolveMutation.isPending}
                    locale={locale}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
