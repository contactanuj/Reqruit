// use-locale.ts — Locale hook backed by user profile settings
// Returns the user's locale from profile data, defaulting to "US".
// Components should use this instead of hardcoding locale (FR30, UX-12).

"use client";

import { useSyncExternalStore } from "react";
import type { LocaleCode } from "../lib/locale";

// ---------------------------------------------------------------------------
// Simple in-memory locale store.
// The app layer sets this once after fetching user profile / settings.
// ---------------------------------------------------------------------------

type Listener = () => void;

let currentLocale: LocaleCode = "US";
const listeners = new Set<Listener>();

function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): LocaleCode {
  return currentLocale;
}

function getServerSnapshot(): LocaleCode {
  return "US";
}

/** Call from the app layer (e.g. after profile fetch) to update the global locale. */
export function setLocale(locale: LocaleCode): void {
  if (locale === currentLocale) return;
  currentLocale = locale;
  listeners.forEach((l) => l());
}

/** Hook — returns the current locale code. Re-renders when locale changes. */
export function useLocale(): LocaleCode {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
