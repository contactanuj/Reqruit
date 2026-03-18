// use-keyboard-shortcut.ts — Keyboard shortcut registry with chord support (FE-2.3, FE-2.5)
// Desktop-only: shortcuts do not fire on touch-only devices (window.innerWidth < 768).
// Chord detection: first key starts a 1s timer; second key within that window triggers action.

import { useEffect, useRef, useCallback } from "react";

export interface ShortcutDefinition {
  /** Single key (e.g. "?", "[", "]", "/") or first key of chord (e.g. "g") */
  key: string;
  /** Second key for chord shortcuts (e.g. "j" for G+J → /jobs) */
  chord?: string;
  /** Require meta (Cmd on Mac) or ctrl (Win/Linux) */
  meta?: boolean;
  /** Human-readable description for the shortcuts overlay */
  description: string;
  /** Action to run on match */
  action: () => void;
}

const CHORD_TIMEOUT_MS = 1000;

/**
 * Registers a list of keyboard shortcuts on the document.
 * Shortcuts do not fire when focus is inside input/textarea/select/contenteditable.
 * On mobile (window.innerWidth < 768) shortcuts are not registered.
 */
export function useKeyboardShortcuts(shortcuts: ShortcutDefinition[]): void {
  // Keep latest shortcuts stable without re-registering listeners
  const shortcutsRef = useRef(shortcuts);
  useEffect(() => {
    shortcutsRef.current = shortcuts;
  }, [shortcuts]);

  const pendingChordRef = useRef<string | null>(null);
  const chordTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearChord = useCallback(() => {
    if (chordTimerRef.current !== null) {
      clearTimeout(chordTimerRef.current);
      chordTimerRef.current = null;
    }
    pendingChordRef.current = null;
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Desktop-only guard
      if (typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches) return;

      // Do not fire when typing in an input element
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase() ?? "";
      if (
        tag === "input" ||
        tag === "textarea" ||
        tag === "select" ||
        target?.isContentEditable
      ) {
        return;
      }

      const key = e.key.toLowerCase();
      const metaOrCtrl = e.metaKey || e.ctrlKey;

      // Check if we're completing a chord
      if (pendingChordRef.current !== null) {
        const firstKey = pendingChordRef.current;
        clearChord();

        const chord = shortcutsRef.current.find(
          (s) =>
            s.key.toLowerCase() === firstKey &&
            s.chord?.toLowerCase() === key &&
            !s.meta,
        );

        if (chord) {
          e.preventDefault();
          chord.action();
          return;
        }
        // No matching chord — fall through to check single-key shortcuts
      }

      // Check meta/ctrl shortcuts first
      const metaShortcut = shortcutsRef.current.find(
        (s) =>
          s.meta &&
          metaOrCtrl &&
          s.key.toLowerCase() === key &&
          !s.chord,
      );
      if (metaShortcut) {
        e.preventDefault();
        metaShortcut.action();
        return;
      }

      // Do not process single/chord keys when meta/ctrl is held (browser shortcuts)
      if (metaOrCtrl) return;

      // Check if key is a chord initiator
      const chordInitiator = shortcutsRef.current.find(
        (s) => s.key.toLowerCase() === key && s.chord && !s.meta,
      );
      if (chordInitiator) {
        e.preventDefault();
        pendingChordRef.current = key;
        chordTimerRef.current = setTimeout(clearChord, CHORD_TIMEOUT_MS);
        return;
      }

      // Single-key shortcuts
      const single = shortcutsRef.current.find(
        (s) => s.key.toLowerCase() === key && !s.chord && !s.meta,
      );
      if (single) {
        e.preventDefault();
        single.action();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      clearChord();
    };
  }, [clearChord]);
}
