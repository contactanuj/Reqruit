// credits-store.ts — Zustand store for daily credit tracking (Rule 6)
// Initialized from profile query at app shell level.

import { create } from "zustand";

interface CreditsState {
  dailyCredits: number;
}

interface CreditsActions {
  /** Decrement credits by 1 (optimistic update before API call). */
  decrementCredit: () => void;
  /** Revert the optimistic decrement on API error. */
  incrementCredit: () => void;
  /** Set the credit count (called when profile data loads). */
  setCredits: (count: number) => void;
}

export const useCreditsStore = create<CreditsState & CreditsActions>((set) => ({
  dailyCredits: 0,

  decrementCredit: () =>
    set((state) => ({ dailyCredits: Math.max(0, state.dailyCredits - 1) })),

  incrementCredit: () =>
    set((state) => ({ dailyCredits: state.dailyCredits + 1 })),

  setCredits: (count) => set({ dailyCredits: count }),
}));
