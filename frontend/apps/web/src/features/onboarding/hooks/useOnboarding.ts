// useOnboarding.ts — Onboarding mutations (FE-3.1, FE-3.4)

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { apiClient, ApiError } from "@reqruit/api-client";
import { useOnboardingStore } from "../store/onboarding-store";
import type { OnboardingGoal, OnboardingPayload, UpdateSettingsPayload } from "../types";

/** Route map: which path to visit after goal selection */
const GOAL_REDIRECT: Record<OnboardingGoal, string> = {
  find_jobs: "/dashboard",
  interview_prep: "/interviews",
  negotiate_offer: "/offers",
  track_applications: "/applications",
};

// ---------------------------------------------------------------------------
// useSetGoal — PATCH /users/me/onboarding
// ---------------------------------------------------------------------------

export function useSetGoal() {
  const router = useRouter();
  const { setGoal, setOnboardingComplete } = useOnboardingStore();
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, OnboardingGoal | null>({
    mutationFn: (goal) => {
      const resolvedGoal: OnboardingGoal = goal ?? "find_jobs";
      const payload: OnboardingPayload = {
        goal: resolvedGoal,
        onboarding_complete: true,
      };
      return apiClient.patch<void>("/users/me/onboarding", payload);
    },

    onSuccess: (_data, goal) => {
      const resolvedGoal: OnboardingGoal = goal ?? "find_jobs";
      setGoal(resolvedGoal);
      setOnboardingComplete(true);
      void queryClient.invalidateQueries({ queryKey: ["profile", "me"] });

      const redirect = GOAL_REDIRECT[resolvedGoal];
      router.push(redirect);
    },

    onError: () => {
      toast.error("Failed to save your goal — please try again");
    },
  });
}

// ---------------------------------------------------------------------------
// useUpdateSettings — PATCH /users/me/settings
// ---------------------------------------------------------------------------

export function useUpdateSettings() {
  const { setShowAllFeatures } = useOnboardingStore();

  return useMutation<void, ApiError, UpdateSettingsPayload>({
    mutationFn: (payload) =>
      apiClient.patch<void>("/users/me/settings", payload),

    // Optimistic update already applied by the component before mutate() call.
    // No need to setShowAllFeatures again here.

    onError: (_error, variables) => {
      // Revert optimistic update on failure
      setShowAllFeatures(!variables.show_all_features);
      toast.error("Failed to save setting — please try again");
    },
  });
}
