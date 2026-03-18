"use client";

// OnboardingFlow.tsx — Client wrapper that orchestrates goal selection (FE-3.1)
// Checks onboarding_complete from profile; redirects if already done.

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@reqruit/api-client";
import { GoalSelector } from "./GoalSelector";
import { useSetGoal } from "../hooks/useOnboarding";
import { useOnboardingStore } from "../store/onboarding-store";

export function OnboardingFlow() {
  const router = useRouter();
  const { onboardingComplete, setOnboardingComplete, setGoal: storeSetGoal } = useOnboardingStore();
  const setGoal = useSetGoal();

  // Server-side fallback: if localStorage says not complete, verify against server profile
  const { data: serverProfile } = useQuery({
    queryKey: ["profile", "me"],
    queryFn: () => apiClient.get<{ onboarding_complete?: boolean; goal?: string }>("/users/me/profile"),
    enabled: !onboardingComplete, // only query when local store says incomplete
    staleTime: 30_000,
  });

  // Reconcile server state with local store
  useEffect(() => {
    if (serverProfile?.onboarding_complete && !onboardingComplete) {
      setOnboardingComplete(true);
      if (serverProfile.goal) {
        storeSetGoal(serverProfile.goal as Parameters<typeof storeSetGoal>[0]);
      }
    }
  }, [serverProfile, onboardingComplete, setOnboardingComplete, storeSetGoal]);

  // If onboarding was already completed (e.g. page revisit), redirect to dashboard
  useEffect(() => {
    if (onboardingComplete) {
      router.push("/dashboard");
    }
  }, [onboardingComplete, router]);

  const handleSelect = (goal: Parameters<typeof setGoal.mutate>[0]) => {
    setGoal.mutate(goal);
  };

  const handleSkip = () => {
    // Skip: use default goal (find_jobs → /dashboard)
    setGoal.mutate(null);
  };

  if (onboardingComplete) {
    return null;
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <GoalSelector
        onSelect={handleSelect}
        onSkip={handleSkip}
        isPending={setGoal.isPending}
      />
    </div>
  );
}
