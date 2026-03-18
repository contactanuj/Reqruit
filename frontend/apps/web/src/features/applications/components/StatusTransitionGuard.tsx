"use client";

// StatusTransitionGuard.tsx — Utility for showing blocked-transition toasts (FE-6.2)
// This module is used inline in KanbanBoard's onDragEnd handler.
// Exported as a convenience helper for consumers and tests.

import { toast } from "sonner";
import type { ApplicationStatus } from "../types";
import { isValidTransition, getTransitionBlockMessage } from "../types";

/**
 * Show a persistent (user-dismissible) warning toast when an invalid status
 * transition is attempted. Returns true if the transition is valid, false if blocked.
 */
export function guardStatusTransition(
  from: ApplicationStatus,
  to: ApplicationStatus
): boolean {
  if (isValidTransition(from, to)) return true;

  const message = getTransitionBlockMessage(from, to);
  toast.warning(
    `Cannot move directly from ${from} to ${to} — ${message}`,
    {
      duration: Infinity, // persistent — user must explicitly dismiss (UX-17)
      action: {
        label: "Got it",
        onClick: () => {},
      },
    }
  );

  return false;
}
