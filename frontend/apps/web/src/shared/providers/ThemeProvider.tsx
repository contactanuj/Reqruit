"use client";

// ThemeProvider.tsx — OS preference detection + class toggle on <html> (FE-2.4)
// Avoids flash of wrong theme by applying preference synchronously on mount.

import { useEffect } from "react";
import { useThemeStore } from "@/features/shell/store/theme-store";
import type { ThemeMode } from "@/features/shell/store/theme-store";

function resolveTheme(theme: ThemeMode): "light" | "dark" {
  if (theme === "system") {
    if (typeof window === "undefined") return "light";
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }
  return theme;
}

function applyTheme(resolved: "light" | "dark") {
  const root = document.documentElement;
  if (resolved === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useThemeStore((s) => s.theme);

  // Apply theme on changes. Initial theme on page load is set by the blocking
  // inline <script> in layout.tsx to prevent FOUC — this effect handles
  // subsequent theme changes made by the user at runtime.
  useEffect(() => {
    const resolved = resolveTheme(theme);
    applyTheme(resolved);
  }, [theme]);

  // Listen for OS preference changes when theme is "system"
  useEffect(() => {
    if (theme !== "system") return;

    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => {
      applyTheme(mediaQuery.matches ? "dark" : "light");
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, [theme]);

  return <>{children}</>;
}
