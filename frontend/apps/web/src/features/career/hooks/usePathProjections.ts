// usePathProjections.ts — hooks for career path projections (FE-13.3)

import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError } from "@reqruit/api-client";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import type { PathProjection } from "../types";

interface GenerateProjectionsInput {
  roleTitles: string[];
  currentSkills?: string[];
  currentExperience?: { title: string; company: string }[];
}

export function useGenerateProjections() {
  const decrementCredit = useCreditsStore((s) => s.decrementCredit);
  const incrementCredit = useCreditsStore((s) => s.incrementCredit);

  return useMutation<PathProjection[], ApiError, GenerateProjectionsInput>({
    mutationFn: (input) =>
      apiClient.post<PathProjection[]>("/career/path-projections", input),

    onMutate: () => {
      decrementCredit();
    },

    onSuccess: () => {
      toast.success("Career path projections generated");
    },

    onError: () => {
      incrementCredit();
      toast.error("Failed to generate projections — please try again");
    },
  });
}
