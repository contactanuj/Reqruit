// applications-store.ts — Zustand store for application feature UI state (FE-6.4)
// Bulk selection state lives here — never in component useState (Rule 6)

import { create } from "zustand";

interface ApplicationsStore {
  // Bulk selection
  selectedIds: Set<string>;
  toggleSelect: (id: string) => void;
  selectAll: (ids: string[]) => void;
  clearSelection: () => void;
  isSelected: (id: string) => boolean;
}

export const useApplicationsStore = create<ApplicationsStore>((set, get) => ({
  selectedIds: new Set<string>(),

  toggleSelect: (id) =>
    set((state) => {
      const next = new Set(state.selectedIds);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return { selectedIds: next };
    }),

  selectAll: (ids) =>
    set({ selectedIds: new Set(ids) }),

  clearSelection: () => set({ selectedIds: new Set<string>() }),

  isSelected: (id) => get().selectedIds.has(id),
}));
