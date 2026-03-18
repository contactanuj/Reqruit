// layout-store.ts — Zustand store for panel/layout preferences (FE-2.1)
// Persisted to localStorage via persist middleware (Rule 6: store per domain)

import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface LayoutStore {
  sidebarCollapsed: boolean;
  copilotVisible: boolean;
  shortcutsOverlayVisible: boolean;
  commandPaletteOpen: boolean;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleCopilot: () => void;
  setCopilotVisible: (visible: boolean) => void;
  toggleShortcutsOverlay: () => void;
  setShortcutsOverlayVisible: (visible: boolean) => void;
  setCommandPaletteOpen: (open: boolean) => void;
}

export const useLayoutStore = create<LayoutStore>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      copilotVisible: true,
      shortcutsOverlayVisible: false,
      commandPaletteOpen: false,

      toggleSidebar: () =>
        set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

      setSidebarCollapsed: (collapsed) =>
        set({ sidebarCollapsed: collapsed }),

      toggleCopilot: () =>
        set((s) => ({ copilotVisible: !s.copilotVisible })),

      setCopilotVisible: (visible) =>
        set({ copilotVisible: visible }),

      toggleShortcutsOverlay: () =>
        set((s) => ({
          shortcutsOverlayVisible: !s.shortcutsOverlayVisible,
        })),

      setShortcutsOverlayVisible: (visible) =>
        set({ shortcutsOverlayVisible: visible }),

      setCommandPaletteOpen: (open) =>
        set({ commandPaletteOpen: open }),
    }),
    {
      name: "reqruit-layout",
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        copilotVisible: state.copilotVisible,
      }),
    },
  ),
);
