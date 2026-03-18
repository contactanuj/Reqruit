// use-focus-trap.ts — Reusable focus-trap + scroll-lock hook for modal dialogs
// Provides: focus trap (Tab cycling), Escape to close, click-outside to close,
// return focus to trigger on close, body scroll lock (NFR-A6, UX-12).

"use client";

import { useEffect, useRef, useCallback } from "react";

const FOCUSABLE_SELECTOR =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

interface UseFocusTrapOptions {
  /** Whether the dialog is open. */
  open: boolean;
  /** Called to close the dialog. */
  onClose: () => void;
}

interface UseFocusTrapReturn {
  /** Attach to the dialog container element. */
  dialogRef: React.RefObject<HTMLDivElement | null>;
  /** Attach to the backdrop to handle click-outside. */
  handleBackdropClick: (e: React.MouseEvent<HTMLDivElement>) => void;
}

export function useFocusTrap({ open, onClose }: UseFocusTrapOptions): UseFocusTrapReturn {
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  // Capture the element that had focus when the dialog opened
  useEffect(() => {
    if (open) {
      triggerRef.current = document.activeElement as HTMLElement | null;
    }
  }, [open]);

  // Focus trap + Escape handler + scroll lock
  useEffect(() => {
    if (!open) return;

    const dialog = dialogRef.current;
    if (!dialog) return;

    // Scroll lock
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Focus the first focusable element inside the dialog
    const focusableElements = dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    const first = focusableElements[0];
    const last = focusableElements[focusableElements.length - 1];
    first?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }

      if (e.key !== "Tab") return;

      // Re-query in case DOM changed (e.g. disabled buttons)
      const currentFocusable = dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      const currentFirst = currentFocusable[0];
      const currentLast = currentFocusable[currentFocusable.length - 1];

      if (e.shiftKey && document.activeElement === currentFirst) {
        e.preventDefault();
        currentLast?.focus();
      } else if (!e.shiftKey && document.activeElement === currentLast) {
        e.preventDefault();
        currentFirst?.focus();
      }
    };

    dialog.addEventListener("keydown", handleKeyDown);

    return () => {
      dialog.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;

      // Return focus to the element that triggered the dialog
      triggerRef.current?.focus();
      triggerRef.current = null;
    };
  }, [open, onClose]);

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) onClose();
    },
    [onClose],
  );

  return { dialogRef, handleBackdropClick };
}
