// useSkillAnalysis.ts — FE-4.6: Skill analysis hooks

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { SkillAnalysis } from "../types";

// ---------------------------------------------------------------------------
// useSkillAnalysis — GET /users/me/skill-analysis
// Returns null when analysis not yet generated (204 response)
// ---------------------------------------------------------------------------

export function useSkillAnalysis() {
  return useQuery<SkillAnalysis | null, ApiError>({
    queryKey: queryKeys.profile.skillAnalysis("me"),
    queryFn: async () => {
      try {
        const data = await apiClient.get<SkillAnalysis | null>("/users/me/skill-analysis");
        return data ?? null;
      } catch (err) {
        if (err instanceof ApiError && err.status === 204) {
          return null;
        }
        throw err;
      }
    },
  });
}

// ---------------------------------------------------------------------------
// useGenerateSkillAnalysis — POST /users/me/skill-analysis/generate
// ---------------------------------------------------------------------------

export function useGenerateSkillAnalysis() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, void>({
    mutationFn: () => apiClient.post<void>("/users/me/skill-analysis/generate", {}),

    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.profile.skillAnalysis("me") });
    },

    onError: () => {
      toast.error("Failed to generate skill analysis — please try again");
    },
  });
}
