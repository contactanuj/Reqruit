"use client";

// KeyboardShortcutsOverlay.tsx — Shortcuts reference overlay (FE-2.5)
// Opened by pressing "?" key. Lists all shortcuts in categories.

import { useRef } from "react";
import { X } from "lucide-react";
import { useFocusTrap } from "../hooks/use-focus-trap";

export interface ShortcutEntry {
  keys: string[];
  description: string;
  category: "navigation" | "view" | "action";
}

export interface KeyboardShortcutsOverlayProps {
  open: boolean;
  onClose: () => void;
}

const SHORTCUTS: ShortcutEntry[] = [
  // Navigation chords
  {
    keys: ["G", "D"],
    description: "Go to Dashboard",
    category: "navigation",
  },
  { keys: ["G", "J"], description: "Go to Jobs", category: "navigation" },
  {
    keys: ["G", "A"],
    description: "Go to Applications",
    category: "navigation",
  },
  { keys: ["G", "P"], description: "Go to Profile", category: "navigation" },
  { keys: ["G", "S"], description: "Go to Settings", category: "navigation" },

  // View shortcuts
  { keys: ["["], description: "Collapse sidebar", category: "view" },
  { keys: ["]"], description: "Expand sidebar", category: "view" },
  {
    keys: ["/"],
    description: "Focus search (Kanban view)",
    category: "view",
  },

  // Action shortcuts
  { keys: ["?"], description: "Show keyboard shortcuts", category: "action" },
  {
    keys: ["Ctrl/⌘", "K"],
    description: "Open command palette",
    category: "action",
  },
];

const CATEGORY_LABELS: Record<ShortcutEntry["category"], string> = {
  navigation: "Navigation",
  view: "View",
  action: "Actions",
};

export function KeyboardShortcutsOverlay({
  open,
  onClose,
}: KeyboardShortcutsOverlayProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const { dialogRef, handleBackdropClick } = useFocusTrap({ open, onClose });

  if (!open) return null;

  const categories = (
    ["navigation", "view", "action"] as ShortcutEntry["category"][]
  ).map((cat) => ({
    cat,
    items: SHORTCUTS.filter((s) => s.category === cat),
  }));

  return (
    <div
      role="presentation"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={handleBackdropClick}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-label="Keyboard shortcuts"
        aria-modal="true"
        className="bg-popover border border-border rounded-lg shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-base font-semibold text-foreground">
            Keyboard Shortcuts
          </h2>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close keyboard shortcuts"
            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {/* Shortcuts grid */}
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          {categories.map(({ cat, items }) => (
            <div key={cat}>
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                {CATEGORY_LABELS[cat]}
              </h3>
              <ul className="space-y-2">
                {items.map((s) => (
                  <li
                    key={s.keys.join("+")}
                    className="flex items-center justify-between gap-4"
                  >
                    <span className="text-sm text-foreground">
                      {s.description}
                    </span>
                    <span className="flex items-center gap-1 shrink-0">
                      {s.keys.map((k, i) => (
                        <span key={i} className="flex items-center gap-1">
                          <kbd className="px-1.5 py-0.5 text-xs font-mono bg-muted border border-border rounded text-foreground">
                            {k}
                          </kbd>
                          {i < s.keys.length - 1 && (
                            <span className="text-muted-foreground text-xs">
                              then
                            </span>
                          )}
                        </span>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
