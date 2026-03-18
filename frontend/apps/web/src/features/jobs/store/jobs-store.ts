// jobs-store.ts — Zustand store for job feature UI preferences (FE-5.3)
// View preference persisted to localStorage (Rule 6)

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type JobsViewMode = "kanban" | "table";

interface JobsStore {
  viewMode: JobsViewMode;
  selectedJobId: string | null;
  setViewMode: (mode: JobsViewMode) => void;
  setSelectedJobId: (id: string | null) => void;
}

export const useJobsStore = create<JobsStore>()(
  persist(
    (set) => ({
      viewMode: "kanban",
      selectedJobId: null,
      setViewMode: (mode) => set({ viewMode: mode }),
      setSelectedJobId: (id) => set({ selectedJobId: id }),
    }),
    {
      name: "reqruit-jobs",
      // Only persist view mode, not selected job
      partialize: (state) => ({ viewMode: state.viewMode }),
    }
  )
);
