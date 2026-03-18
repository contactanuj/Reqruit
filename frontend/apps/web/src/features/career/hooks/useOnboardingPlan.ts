// useOnboardingPlan.ts — hooks for onboarding plan generation (FE-13.1)

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import type { OnboardingPlan, OnboardingMilestone } from "../types";

interface CreateOnboardingPlanInput {
  roleTitle: string;
  company: string;
  startDate: string;
}

export function useOnboardingPlanMutation() {
  const queryClient = useQueryClient();
  const decrementCredit = useCreditsStore((s) => s.decrementCredit);
  const incrementCredit = useCreditsStore((s) => s.incrementCredit);

  return useMutation<OnboardingPlan, ApiError, CreateOnboardingPlanInput>({
    mutationFn: (input) =>
      apiClient.post<OnboardingPlan>("/career/onboarding-plans", input),

    onMutate: () => {
      decrementCredit();
    },

    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.career.onboardingPlan(data.id), data);
      toast.success("Onboarding plan generated");
    },

    onError: () => {
      incrementCredit();
      toast.error("Failed to generate onboarding plan — please try again");
    },
  });
}

export function useToggleMilestone(planId: string) {
  const queryClient = useQueryClient();

  return useMutation<
    OnboardingMilestone,
    ApiError,
    { milestoneId: string; completed: boolean }
  >({
    mutationFn: ({ milestoneId, completed }) =>
      apiClient.patch<OnboardingMilestone>(
        `/career/onboarding-plans/${planId}/milestones/${milestoneId}`,
        { completed },
      ),

    onMutate: async ({ milestoneId, completed }) => {
      const key = queryKeys.career.onboardingPlan(planId);
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<OnboardingPlan>(key);

      if (previous) {
        queryClient.setQueryData<OnboardingPlan>(key, {
          ...previous,
          milestones: previous.milestones.map((m) =>
            m.id === milestoneId ? { ...m, completed } : m,
          ),
        });
      }

      return { previous };
    },

    onError: (_err, _vars, context) => {
      const ctx = context as { previous?: OnboardingPlan } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData(
          queryKeys.career.onboardingPlan(planId),
          ctx.previous,
        );
      }
      toast.error("Failed to update milestone");
    },
  });
}
