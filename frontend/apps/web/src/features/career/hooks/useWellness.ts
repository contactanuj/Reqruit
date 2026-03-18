// useWellness.ts — hooks for wellness check-in and burnout risk (FE-13.2)

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { WellnessCheckIn, BurnoutRisk, WellnessTrend, MoodLevel } from "../types";

interface CheckInInput {
  mood: MoodLevel;
  energy: MoodLevel;
}

export function useWellnessCheckIn() {
  const queryClient = useQueryClient();

  return useMutation<WellnessCheckIn, ApiError, CheckInInput>({
    mutationFn: (input) =>
      apiClient.post<WellnessCheckIn>("/wellness/check-ins", input),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.career.wellness() });
      queryClient.invalidateQueries({ queryKey: queryKeys.career.wellnessTrend() });
      toast.success("Wellness check-in recorded");
    },

    onError: () => {
      toast.error("Failed to submit check-in — please try again");
    },
  });
}

export function useBurnoutRisk() {
  return useQuery<BurnoutRisk, ApiError>({
    queryKey: queryKeys.career.wellness(),
    queryFn: () => apiClient.get<BurnoutRisk>("/wellness/burnout-risk"),
    staleTime: 300_000, // 5 minutes
  });
}

export function useWellnessTrend() {
  return useQuery<WellnessTrend, ApiError>({
    queryKey: queryKeys.career.wellnessTrend(),
    queryFn: () => apiClient.get<WellnessTrend>("/wellness/trend"),
    staleTime: 300_000,
  });
}
