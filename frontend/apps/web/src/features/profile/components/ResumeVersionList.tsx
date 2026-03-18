"use client";

// ResumeVersionList.tsx — FE-4.5: Multiple resume versions management

import { useState, useCallback } from "react";
import { formatDate } from "@repo/ui/lib/locale";
import type { LocaleCode } from "@repo/ui/lib/locale";
import { useFocusTrap } from "@repo/ui/hooks";
import { useResumeList, useSetMasterResume, useDeleteResume } from "../hooks/useProfile";

interface ResumeVersionListProps {
  locale: LocaleCode;
}

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  processing: "Processing",
  completed: "Parsed",
  failed: "Failed",
};

const STATUS_CLASSES: Record<string, string> = {
  pending: "bg-muted text-muted-foreground",
  processing: "bg-primary/10 text-primary",
  completed: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  failed: "bg-destructive/10 text-destructive",
};

export function ResumeVersionList({ locale }: ResumeVersionListProps) {
  const { data: resumes, isPending } = useResumeList();
  const { mutate: setMaster, isPending: isSettingMaster } = useSetMasterResume();
  const { mutate: deleteResume, isPending: isDeleting } = useDeleteResume();

  const [masterDeleteError, setMasterDeleteError] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const handleCancelDelete = useCallback(() => {
    setConfirmDeleteId(null);
  }, []);

  const { dialogRef: deleteDialogRef, handleBackdropClick: handleDeleteBackdropClick } =
    useFocusTrap({ open: confirmDeleteId !== null, onClose: handleCancelDelete });

  const handleDelete = (resumeId: string, isMaster: boolean) => {
    if (isMaster) {
      setMasterDeleteError(
        "Cannot delete the master resume — set another as master first"
      );
      return;
    }
    setMasterDeleteError(null);
    setConfirmDeleteId(resumeId);
  };

  const handleConfirmDelete = () => {
    if (!confirmDeleteId) return;
    deleteResume(confirmDeleteId, {
      onSettled: () => setConfirmDeleteId(null),
    });
  };

  if (isPending) {
    return (
      <div className="flex flex-col gap-3">
        {[1, 2].map((i) => (
          <div
            key={i}
            className="h-16 animate-pulse rounded-lg border border-border bg-muted"
          />
        ))}
      </div>
    );
  }

  if (!resumes || resumes.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No resumes uploaded yet.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {masterDeleteError && (
        <p role="alert" className="text-sm text-destructive">
          {masterDeleteError}
        </p>
      )}

      {/* Confirm delete dialog — focus-trapped, Escape/backdrop to close */}
      {confirmDeleteId && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={handleDeleteBackdropClick}
        >
          <div
            ref={deleteDialogRef}
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="confirm-delete-title"
            className="mx-4 max-w-sm rounded-lg bg-background p-6 shadow-lg"
          >
            <h2 id="confirm-delete-title" className="text-base font-semibold">
              Delete this resume?
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              This cannot be undone.
            </p>
            <div className="mt-4 flex gap-3">
              <button
                type="button"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
                className="flex-1 rounded-md bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50"
              >
                Confirm
              </button>
              <button
                type="button"
                onClick={handleCancelDelete}
                disabled={isDeleting}
                className="flex-1 rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <ul className="flex flex-col gap-2">
        {resumes.map((resume) => (
          <li
            key={resume.id}
            className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card p-3"
          >
            <div className="flex flex-col gap-0.5 min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-medium">{resume.filename}</span>
                {resume.isMaster && (
                  <span className="inline-flex items-center rounded-full bg-primary px-2 py-0.5 text-xs font-semibold text-primary-foreground">
                    Master
                  </span>
                )}
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASSES[resume.parseStatus] ?? ""}`}
                >
                  {STATUS_LABELS[resume.parseStatus] ?? resume.parseStatus}
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                Uploaded {formatDate(resume.uploadedAt, locale)}
              </span>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              {!resume.isMaster && (
                <button
                  type="button"
                  onClick={() => setMaster(resume.id)}
                  disabled={isSettingMaster || isDeleting}
                  className="rounded px-2 py-1 text-xs font-medium text-primary hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
                >
                  Set as master
                </button>
              )}
              <button
                type="button"
                onClick={() => handleDelete(resume.id, resume.isMaster)}
                disabled={isSettingMaster || isDeleting}
                aria-label={`Delete ${resume.filename}`}
                className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive disabled:opacity-50"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                  <path d="M10 11v6" />
                  <path d="M14 11v6" />
                  <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                </svg>
                <span className="sr-only">Delete {resume.filename}</span>
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
