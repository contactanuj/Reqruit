"use client";

// BulkActionBar.tsx — Bulk action bar that appears when applications are selected (FE-6.4)

import { useState, useCallback } from "react";
import { useApplicationsStore } from "../store/applications-store";
import { useBulkDelete, useBulkWithdraw, useBulkExport } from "../hooks/useBulkOperations";
import { useFocusTrap } from "@repo/ui/hooks";

interface BulkActionBarProps {
  /** Called after successful bulk delete to refresh external state */
  onAfterDelete?: () => void;
}

export function BulkActionBar({ onAfterDelete }: BulkActionBarProps) {
  const { selectedIds, clearSelection } = useApplicationsStore();
  const count = selectedIds.size;

  const bulkDelete = useBulkDelete();
  const bulkWithdraw = useBulkWithdraw();
  const bulkExport = useBulkExport();

  const [confirmDelete, setConfirmDelete] = useState(false);
  const [confirmWithdraw, setConfirmWithdraw] = useState(false);

  const handleCloseDelete = useCallback(() => setConfirmDelete(false), []);
  const handleCloseWithdraw = useCallback(() => setConfirmWithdraw(false), []);

  const { dialogRef: deleteDialogRef, handleBackdropClick: handleDeleteBackdropClick } =
    useFocusTrap({ open: confirmDelete, onClose: handleCloseDelete });
  const { dialogRef: withdrawDialogRef, handleBackdropClick: handleWithdrawBackdropClick } =
    useFocusTrap({ open: confirmWithdraw, onClose: handleCloseWithdraw });

  if (count === 0) return null;

  const ids = Array.from(selectedIds);

  function handleWithdrawConfirm() {
    bulkWithdraw.mutate(ids, {
      onSuccess: () => {
        setConfirmWithdraw(false);
      },
    });
  }

  function handleDeleteConfirm() {
    bulkDelete.mutate(ids, {
      onSuccess: () => {
        setConfirmDelete(false);
        onAfterDelete?.();
      },
    });
  }

  return (
    <>
      {/* Bulk action bar — fixed at bottom of screen */}
      <div
        role="toolbar"
        aria-label="Bulk actions"
        data-testid="bulk-action-bar"
        className={[
          "fixed bottom-6 left-1/2 -translate-x-1/2 z-50",
          "flex items-center gap-3 rounded-xl border border-border bg-card px-5 py-3 shadow-xl",
          "animate-in slide-in-from-bottom-4 duration-200",
        ].join(" ")}
      >
        <span className="text-sm font-medium text-muted-foreground" aria-live="polite">
          {count} selected
        </span>

        <div className="h-4 w-px bg-border" aria-hidden="true" />

        <button
          type="button"
          onClick={() => setConfirmDelete(true)}
          disabled={bulkDelete.isPending}
          className="rounded-md bg-destructive px-3 py-1.5 text-xs font-medium text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50"
          data-testid="bulk-delete-btn"
        >
          Delete
        </button>

        <button
          type="button"
          onClick={() => setConfirmWithdraw(true)}
          disabled={bulkWithdraw.isPending}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-50"
          data-testid="bulk-withdraw-btn"
        >
          Withdraw
        </button>

        <button
          type="button"
          onClick={() => bulkExport.mutate(ids)}
          disabled={bulkExport.isPending}
          className="rounded-md border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-50"
          data-testid="bulk-export-btn"
        >
          Export CSV
        </button>

        <button
          type="button"
          onClick={clearSelection}
          className="text-xs text-muted-foreground hover:text-foreground"
          aria-label="Deselect all"
          data-testid="bulk-clear-btn"
        >
          ✕ Clear
        </button>
      </div>

      {/* AlertDialog for bulk withdraw confirmation */}
      {confirmWithdraw && (
        <div
          data-testid="bulk-withdraw-dialog"
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50"
          onClick={handleWithdrawBackdropClick}
        >
          <div
            ref={withdrawDialogRef}
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="bulk-withdraw-title"
            aria-describedby="bulk-withdraw-desc"
            className="w-full max-w-sm rounded-xl bg-card p-6 shadow-2xl border border-border"
          >
            <h2 id="bulk-withdraw-title" className="text-base font-semibold mb-2">
              Withdraw {count} application{count !== 1 ? "s" : ""}?
            </h2>
            <p id="bulk-withdraw-desc" className="text-sm text-muted-foreground mb-5">
              Withdrawn applications move to a terminal state and cannot be reactivated.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmWithdraw(false)}
                className="rounded-md border border-border px-4 py-2 text-sm hover:bg-muted"
                data-testid="bulk-withdraw-cancel"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleWithdrawConfirm}
                disabled={bulkWithdraw.isPending}
                className="rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50"
                data-testid="bulk-withdraw-confirm"
              >
                {bulkWithdraw.isPending ? "Withdrawing\u2026" : "Withdraw"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AlertDialog for destructive bulk delete confirmation */}
      {confirmDelete && (
        <div
          data-testid="bulk-delete-dialog"
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50"
          onClick={handleDeleteBackdropClick}
        >
          <div
            ref={deleteDialogRef}
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="bulk-delete-title"
            aria-describedby="bulk-delete-desc"
            className="w-full max-w-sm rounded-xl bg-card p-6 shadow-2xl border border-border"
          >
            <h2 id="bulk-delete-title" className="text-base font-semibold mb-2">
              Delete {count} application{count !== 1 ? "s" : ""}? This cannot be undone.
            </h2>
            <p id="bulk-delete-desc" className="text-sm text-muted-foreground mb-5">
              All selected application data will be permanently removed.
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="rounded-md border border-border px-4 py-2 text-sm hover:bg-muted"
                data-testid="bulk-delete-cancel"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                disabled={bulkDelete.isPending}
                className="rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50"
                data-testid="bulk-delete-confirm"
              >
                {bulkDelete.isPending ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
