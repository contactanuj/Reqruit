// useProgressiveDisclosure.ts — Feature visibility based on goal + milestone unlocks (FE-3.1, FE-3.3, FE-3.4)
// Central hook for all feature visibility queries (Rule 6: no cross-feature deep imports)

import { useEffect, useRef } from "react";
import { useOnboardingStore } from "../store/onboarding-store";
import { showFeatureUnlockToast } from "@repo/ui/components/FeatureUnlockToast";
import { GOAL_OPTIONS } from "../types";
import type { FeatureKey } from "../types";

export interface FeatureVisibility {
  /** Whether the feature should be shown as enabled/accessible */
  enabled: boolean;
  /** Whether this is a newly unlocked feature (within last 10 seconds) */
  newlyUnlocked: boolean;
  /** Tooltip hint shown on locked nav items */
  lockedHint?: string;
}

const LOCKED_HINTS: Partial<Record<FeatureKey, string>> = {
  interviews: "Unlocks when you move an application to Interviewing",
  offers: "Unlocks when you receive your first offer",
  career: "Unlocks after completing your profile",
};

/** Human-readable labels for toast messages */
const FEATURE_LABELS: Record<FeatureKey, string> = {
  dashboard: "Dashboard",
  jobs: "Jobs",
  applications: "Applications",
  interviews: "Interviews",
  offers: "Offers",
  career: "Career",
  profile: "Profile",
};

export function useProgressiveDisclosure(): Record<
  FeatureKey,
  FeatureVisibility
> {
  const { goal, unlockedFeatures, showAllFeatures } = useOnboardingStore();

  // Track which features we've already toasted to avoid duplicates
  const toastedRef = useRef<Set<FeatureKey>>(new Set());

  const goalFeatures = goal
    ? GOAL_OPTIONS.find((o) => o.id === goal)?.features ?? []
    : (["dashboard", "jobs"] as FeatureKey[]);

  const now = Date.now();
  const NEWLY_UNLOCKED_WINDOW_MS = 10_000;

  const allFeatures: FeatureKey[] = [
    "dashboard",
    "jobs",
    "applications",
    "interviews",
    "offers",
    "career",
    "profile",
  ];

  const result = Object.fromEntries(
    allFeatures.map((key) => {
      if (showAllFeatures) {
        return [
          key,
          { enabled: true, newlyUnlocked: false, lockedHint: undefined },
        ];
      }

      const isGoalFeature = goalFeatures.includes(key);
      const unlock = unlockedFeatures[key];
      const isMilestoneUnlocked = Boolean(unlock);
      const enabled = isGoalFeature || isMilestoneUnlocked;
      const newlyUnlocked =
        isMilestoneUnlocked &&
        !unlock?.seen &&
        unlock?.unlockedAt !== undefined &&
        now - unlock.unlockedAt < NEWLY_UNLOCKED_WINDOW_MS;

      return [
        key,
        {
          enabled,
          newlyUnlocked: Boolean(newlyUnlocked),
          lockedHint: !enabled ? LOCKED_HINTS[key] : undefined,
        },
      ];
    }),
  ) as Record<FeatureKey, FeatureVisibility>;

  // Fire toast for newly unlocked features (once per feature)
  useEffect(() => {
    for (const key of allFeatures) {
      if (result[key].newlyUnlocked && !toastedRef.current.has(key)) {
        toastedRef.current.add(key);
        showFeatureUnlockToast(FEATURE_LABELS[key]);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goal, unlockedFeatures, showAllFeatures]);

  return result;
}

/**
 * Check whether a status transition triggers a feature unlock.
 * Returns the feature key if an unlock should happen, or null.
 */
export function getUnlockFromStatusTransition(
  newStatus: string,
): FeatureKey | null {
  if (newStatus === "Interviewing") return "interviews";
  if (newStatus === "Offered") return "offers";
  return null;
}
