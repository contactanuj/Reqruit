"use client";

// TaskQueueTable.tsx — FE-15.3: Background task queue with retry/cancel

import { useState } from "react";
import { useTaskQueueQuery, useRetryTask, useCancelTask } from "../hooks/useTaskQueue";
import { TaskLogPanel } from "./TaskLogPanel";
import { formatDate } from "@repo/ui/lib/locale";
import { useLocale } from "@repo/ui/hooks";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  running: "bg-blue-100 text-blue-800",
  failed: "bg-red-100 text-red-800",
  completed: "bg-green-100 text-green-800",
};

export function TaskQueueTable() {
  const { data: tasks, isLoading, isError } = useTaskQueueQuery();
  const retryMutation = useRetryTask();
  const cancelMutation = useCancelTask();
  const [viewingLogTaskId, setViewingLogTaskId] = useState<string | null>(null);
  const locale = useLocale();
  const [cancelTargetId, setCancelTargetId] = useState<string | null>(null);

  const handleCancelConfirm = () => {
    if (!cancelTargetId) return;
    cancelMutation.mutate({ id: cancelTargetId });
    setCancelTargetId(null);
  };

  if (isLoading) {
    return (
      <div data-testid="task-queue-skeleton" className="animate-pulse space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 rounded bg-gray-200" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div data-testid="task-queue-error" className="rounded border border-red-300 bg-red-50 p-4 text-red-700">
        Failed to load task queue.
      </div>
    );
  }

  return (
    <>
      <div data-testid="task-queue-table" className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">ID</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Type</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Status</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Created</th>
              <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {tasks?.map((task) => (
              <tr key={task.id} data-testid={`task-row-${task.id}`}>
                <td className="px-4 py-2 text-sm font-mono">{task.id}</td>
                <td className="px-4 py-2 text-sm">{task.type}</td>
                <td className="px-4 py-2">
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[task.status] ?? "bg-gray-100 text-gray-800"}`}
                  >
                    {task.status}
                  </span>
                </td>
                <td className="px-4 py-2 text-sm text-gray-600">
                  {formatDate(task.createdAt, locale)}
                </td>
                <td className="flex gap-2 px-4 py-2">
                  <button
                    data-testid={`view-logs-${task.id}`}
                    onClick={() => setViewingLogTaskId(task.id)}
                    className="rounded border px-2 py-1 text-xs hover:bg-gray-100"
                  >
                    Logs
                  </button>

                  {task.status === "failed" && (
                    <button
                      data-testid={`retry-button-${task.id}`}
                      onClick={() => retryMutation.mutate({ id: task.id })}
                      disabled={retryMutation.isPending}
                      className="rounded bg-orange-500 px-2 py-1 text-xs text-white hover:bg-orange-600 disabled:opacity-50"
                    >
                      Retry
                    </button>
                  )}

                  {task.status === "pending" && (
                    <button
                      data-testid={`cancel-button-${task.id}`}
                      onClick={() => setCancelTargetId(task.id)}
                      disabled={cancelMutation.isPending}
                      className="rounded bg-red-500 px-2 py-1 text-xs text-white hover:bg-red-600 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <TaskLogPanel
        taskId={viewingLogTaskId}
        onClose={() => setViewingLogTaskId(null)}
      />

      {/* Cancel confirmation dialog */}
      {cancelTargetId && (
        <div
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="cancel-dialog-title"
          aria-describedby="cancel-dialog-desc"
          data-testid="cancel-confirm-dialog"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onKeyDown={(e) => {
            if (e.key === "Escape") setCancelTargetId(null);
          }}
        >
          <div className="mx-4 w-full max-w-sm rounded-lg border bg-white p-6 shadow-lg">
            <h2 id="cancel-dialog-title" className="text-base font-semibold">
              Cancel Task
            </h2>
            <p id="cancel-dialog-desc" className="mt-2 text-sm text-gray-600">
              Are you sure you want to cancel this task? This action cannot be undone.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                data-testid="cancel-dialog-dismiss"
                onClick={() => setCancelTargetId(null)}
                className="rounded border px-3 py-1.5 text-sm hover:bg-gray-100"
                autoFocus
              >
                Keep task
              </button>
              <button
                type="button"
                data-testid="cancel-dialog-confirm"
                onClick={handleCancelConfirm}
                className="rounded bg-red-500 px-3 py-1.5 text-sm text-white hover:bg-red-600"
              >
                Cancel task
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
