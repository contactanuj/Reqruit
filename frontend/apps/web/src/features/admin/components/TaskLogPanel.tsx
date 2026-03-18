"use client";

// TaskLogPanel.tsx — FE-15.3: Right-side slide-in panel for task logs

import { useCallback } from "react";
import { useFocusTrap } from "@repo/ui/hooks";
import { useTaskLogs } from "../hooks/useTaskQueue";

interface TaskLogPanelProps {
  taskId: string | null;
  onClose: () => void;
}

export function TaskLogPanel({ taskId, onClose }: TaskLogPanelProps) {
  const open = !!taskId;
  const { data: logs, isLoading } = useTaskLogs(taskId);

  const handleClose = useCallback(() => {
    onClose();
  }, [onClose]);

  const { dialogRef, handleBackdropClick } = useFocusTrap({
    open,
    onClose: handleClose,
  });

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/30"
      onClick={handleBackdropClick}
      data-testid="task-log-backdrop"
    >
      <div
        ref={dialogRef}
        data-testid="task-log-panel"
        className="flex h-full w-full max-w-lg flex-col bg-white shadow-xl"
        role="dialog"
        aria-label="Task logs"
      >
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="text-lg font-semibold">Task Logs — {taskId}</h2>
          <button
            data-testid="close-log-panel"
            onClick={handleClose}
            className="rounded p-1 hover:bg-gray-100"
            aria-label="Close log panel"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-auto p-4">
          {isLoading ? (
            <div data-testid="log-loading" className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-4 rounded bg-gray-200" />
              ))}
            </div>
          ) : (
            <pre
              data-testid="log-content"
              className="whitespace-pre-wrap break-words font-mono text-sm text-gray-800"
            >
              {logs ?? "No logs available."}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
