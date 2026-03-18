"use client";

// DocumentVersionList.tsx — FE-7.5: Cover letter version management

import { useState, useCallback } from "react";
import { toast } from "sonner";
import { formatDate } from "@repo/ui/lib/locale";
import type { LocaleCode } from "@repo/ui/lib/locale";
import { useFocusTrap } from "@repo/ui/hooks";
import { apiClient } from "@reqruit/api-client";
import {
  useCoverLetterVersions,
  useDeleteCoverLetterVersion,
  type CoverLetterVersion,
} from "../hooks/useCoverLetterGeneration";

interface DocumentVersionListProps {
  applicationId: string;
  locale: LocaleCode;
}

export function DocumentVersionList({
  applicationId,
  locale,
}: DocumentVersionListProps) {
  const { data: versions, isPending } = useCoverLetterVersions(applicationId);
  const { mutate: deleteVersion, isPending: isDeleting } =
    useDeleteCoverLetterVersion(applicationId);

  const [viewingVersion, setViewingVersion] =
    useState<CoverLetterVersion | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [activeDeleteError, setActiveDeleteError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const handleCancelDelete = useCallback(() => {
    setConfirmDeleteId(null);
  }, []);
  const handleCloseView = useCallback(() => {
    setViewingVersion(null);
  }, []);

  const { dialogRef: deleteDialogRef, handleBackdropClick: handleDeleteBackdropClick } =
    useFocusTrap({ open: confirmDeleteId !== null, onClose: handleCancelDelete });
  const { dialogRef: viewDialogRef, handleBackdropClick: handleViewBackdropClick } =
    useFocusTrap({ open: viewingVersion !== null, onClose: handleCloseView });

  const handleDelete = (version: CoverLetterVersion) => {
    if (version.is_approved) {
      setActiveDeleteError(
        "Cannot delete the active cover letter — approve a different version first"
      );
      return;
    }
    setActiveDeleteError(null);
    setConfirmDeleteId(version.id);
  };

  const handleConfirmDelete = () => {
    if (!confirmDeleteId) return;
    deleteVersion(confirmDeleteId, {
      onSettled: () => setConfirmDeleteId(null),
    });
  };

  const handleDownload = async (version: CoverLetterVersion) => {
    setDownloadingId(version.id);
    try {
      const res = await apiClient.get<Blob>(
        `/applications/${applicationId}/cover-letters/${version.id}/download`,
        { responseType: 'blob' }
      );
      const blob = res instanceof Blob ? res : new Blob([res as BlobPart]);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `cover-letter-v${version.version_number}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Download failed. Please try again.");
    } finally {
      setDownloadingId(null);
    }
  };

  if (isPending) {
    return (
      <div className="flex flex-col gap-3" aria-busy="true">
        {[1, 2].map((i) => (
          <div
            key={i}
            className="h-16 animate-pulse rounded-lg border border-border bg-muted"
          />
        ))}
      </div>
    );
  }

  if (!versions || versions.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No cover letters generated yet.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {activeDeleteError && (
        <p
          role="alert"
          className="text-sm text-destructive"
          data-testid="active-delete-error"
        >
          {activeDeleteError}
        </p>
      )}

      {/* Confirm delete dialog — focus-trapped, Escape/backdrop to close */}
      {confirmDeleteId && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          data-testid="confirm-delete-dialog"
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
              Delete this version?
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
                data-testid="confirm-delete-button"
              >
                Delete
              </button>
              <button
                type="button"
                onClick={() => setConfirmDeleteId(null)}
                disabled={isDeleting}
                className="flex-1 rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
                data-testid="cancel-delete-button"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View modal — focus-trapped, Escape/backdrop to close */}
      {viewingVersion && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          data-testid="view-version-modal"
          onClick={handleViewBackdropClick}
        >
          <div
            ref={viewDialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="view-version-title"
            className="relative flex h-full w-full flex-col bg-background shadow-xl md:mx-4 md:h-auto md:max-h-[90vh] md:max-w-3xl md:rounded-lg"
          >
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <h2
                id="view-version-title"
                className="text-base font-semibold"
              >
                Cover Letter v{viewingVersion.version_number}
              </h2>
              <button
                type="button"
                onClick={() => setViewingVersion(null)}
                aria-label="Close"
                className="rounded p-1 hover:bg-muted"
                data-testid="close-view-modal"
              >
                ✕
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <div
                className="whitespace-pre-wrap text-sm leading-relaxed"
                data-testid="version-content"
              >
                {viewingVersion.content}
              </div>
            </div>
          </div>
        </div>
      )}

      <ul className="flex flex-col gap-2" data-testid="version-list">
        {versions.map((version) => (
          <li
            key={version.id}
            className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card p-3"
            data-testid={`version-item-${version.id}`}
          >
            <div className="flex flex-col gap-0.5 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">
                  v{version.version_number}
                </span>
                {version.is_approved && (
                  <span
                    className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800"
                    data-testid="active-badge"
                  >
                    Active
                  </span>
                )}
              </div>
              <span className="text-xs text-muted-foreground">
                {formatDate(version.generated_at, locale)}
              </span>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              {/* View */}
              <button
                type="button"
                onClick={() => setViewingVersion(version)}
                className="rounded px-2 py-1 text-xs font-medium text-primary hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                data-testid={`view-button-${version.id}`}
              >
                View
              </button>

              {/* Download */}
              <button
                type="button"
                onClick={() => void handleDownload(version)}
                disabled={downloadingId === version.id}
                className="rounded px-2 py-1 text-xs font-medium text-primary hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
                data-testid={`download-button-${version.id}`}
              >
                {downloadingId === version.id ? "…" : "Download"}
              </button>

              {/* Delete */}
              <button
                type="button"
                onClick={() => handleDelete(version)}
                disabled={isDeleting}
                aria-label={`Delete version v${version.version_number}`}
                className="rounded px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-destructive/10 hover:text-destructive focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-destructive disabled:opacity-50"
                data-testid={`delete-button-${version.id}`}
              >
                Delete
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
