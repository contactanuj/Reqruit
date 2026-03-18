// ActionBar.tsx — Approve / Revise / Edit directly actions (FE-7.3, FE-7.4)
// UX-9: ⌘Enter keyboard shortcut for Approve (desktop only).
// NFR-A5: Approve button ≥ 44×44px.

import * as React from "react";

interface ActionBarProps {
  onApprove: () => void;
  onRevise: () => void;
  onToggleEdit: () => void;
  isEditing?: boolean;
  isApproving?: boolean;
  isRevising?: boolean;
}

export function ActionBar({
  onApprove,
  onRevise,
  onToggleEdit,
  isEditing = false,
  isApproving = false,
  isRevising = false,
}: ActionBarProps) {
  // ⌘Enter → Approve (desktop only, UX-9)
  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (window.innerWidth < 768) return; // Skip on mobile
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        onApprove();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onApprove]);

  return (
    <div
      className="sticky bottom-0 z-10 flex items-center gap-2 border-t border-border bg-background px-4 py-3"
      data-testid="action-bar"
    >
      {/* Approve — primary green, ≥44×44px (NFR-A5) */}
      <button
        type="button"
        onClick={onApprove}
        disabled={isApproving}
        aria-label="Approve cover letter"
        className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-green-600 px-5 py-2 text-sm font-semibold text-white hover:bg-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-600 disabled:opacity-50"
        data-testid="approve-button"
      >
        {isApproving ? "Approving…" : "Approve"}
      </button>

      {/* Revise — secondary */}
      <button
        type="button"
        onClick={onRevise}
        disabled={isRevising}
        aria-label="Request revision"
        className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md border border-border bg-background px-5 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
        data-testid="revise-button"
      >
        {isRevising ? "Revising…" : "Revise"}
      </button>

      {/* Edit directly — tertiary toggle */}
      <button
        type="button"
        onClick={onToggleEdit}
        aria-pressed={isEditing}
        aria-label={isEditing ? "Stop editing" : "Edit directly"}
        className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md px-5 py-2 text-sm font-medium text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary aria-pressed:bg-primary/10 aria-pressed:text-primary"
        data-testid="edit-directly-button"
      >
        {isEditing ? "Done editing" : "Edit directly"}
      </button>
    </div>
  );
}
