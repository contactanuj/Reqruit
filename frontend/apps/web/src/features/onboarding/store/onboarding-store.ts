// onboarding-store.ts — Zustand store for progressive disclosure state (FE-3.1, FE-3.4)
// Persisted to localStorage via persist middleware

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { FeatureKey, OnboardingGoal } from "../types";

export interface UnlockedFeature {
  key: FeatureKey;
  /** Timestamp when unlocked (for highlight animation) */
  unlockedAt?: number;
  /** Whether the user has visited the feature since unlock */
  seen: boolean;
}

export interface OnboardingStore {
  /** Whether user has completed goal selection */
  onboardingComplete: boolean;
  /** User's selected goal */
  goal: OnboardingGoal | null;
  /** Features explicitly unlocked via milestone events */
  unlockedFeatures: Partial<Record<FeatureKey, UnlockedFeature>>;
  /** Power-user override: show all features regardless of milestones */
  showAllFeatures: boolean;
  /** Whether user has approved their first cover letter (UX-15 PWA prompt) */
  hasApprovedFirstCoverLetter: boolean;

  setGoal: (goal: OnboardingGoal) => void;
  setOnboardingComplete: (complete: boolean) => void;
  unlockFeature: (key: FeatureKey) => void;
  markFeatureSeen: (key: FeatureKey) => void;
  setShowAllFeatures: (show: boolean) => void;
  setHasApprovedFirstCoverLetter: (approved: boolean) => void;
}

export const useOnboardingStore = create<OnboardingStore>()(
  persist(
    (set) => ({
      onboardingComplete: false,
      goal: null,
      unlockedFeatures: {},
      showAllFeatures: false,
      hasApprovedFirstCoverLetter: false,

      setGoal: (goal) => set({ goal }),

      setOnboardingComplete: (complete) =>
        set({ onboardingComplete: complete }),

      unlockFeature: (key) =>
        set((state) => ({
          unlockedFeatures: {
            ...state.unlockedFeatures,
            [key]: {
              key,
              unlockedAt: Date.now(),
              seen: false,
            },
          },
        })),

      markFeatureSeen: (key) =>
        set((state) => ({
          unlockedFeatures: {
            ...state.unlockedFeatures,
            [key]: {
              ...(state.unlockedFeatures[key] ?? { key, seen: false }),
              seen: true,
            },
          },
        })),

      setShowAllFeatures: (show) => set({ showAllFeatures: show }),

      setHasApprovedFirstCoverLetter: (approved) =>
        set({ hasApprovedFirstCoverLetter: approved }),
    }),
    {
      name: "reqruit-onboarding",
    },
  ),
);
