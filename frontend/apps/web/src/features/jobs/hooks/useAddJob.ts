// useAddJob.ts — Add job mutations (FE-5.2)

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { SavedJob, AddJobPayload, ParseJobUrlPayload, ParseJobUrlResult } from "../types";

// ---------------------------------------------------------------------------
// useParseJobUrl — FE-5.2: POST /jobs/parse-url
// ---------------------------------------------------------------------------

export function useParseJobUrl() {
  return useMutation<ParseJobUrlResult, ApiError, ParseJobUrlPayload>({
    mutationFn: (payload) =>
      apiClient.post<ParseJobUrlResult>("/jobs/parse-url", payload),
  });
}

// ---------------------------------------------------------------------------
// useAddJob — FE-5.2: POST /jobs
// ---------------------------------------------------------------------------

export function useAddJob(onSuccess?: () => void) {
  const queryClient = useQueryClient();

  return useMutation<SavedJob, ApiError, AddJobPayload>({
    mutationFn: (payload) => apiClient.post<SavedJob>("/jobs", payload),

    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.jobs.list() });
      const previous = queryClient.getQueryData<SavedJob[]>(queryKeys.jobs.list());

      // Optimistic: add to saved jobs list immediately
      if (previous) {
        const optimisticJob: SavedJob = {
          id: `optimistic-${Date.now()}`,
          title: payload.title,
          company: payload.company,
          location: payload.location ?? "",
          description: payload.description,
          url: payload.url,
          salary_min: payload.salary_min,
          salary_max: payload.salary_max,
          remote_preference: payload.remote_preference,
          created_at: new Date().toISOString(),
          status: "saved",
        };
        queryClient.setQueryData<SavedJob[]>(queryKeys.jobs.list(), [
          optimisticJob,
          ...previous,
        ]);
      }

      return { previous };
    },

    onError: (_error, _payload, context) => {
      const ctx = context as { previous?: SavedJob[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<SavedJob[]>(queryKeys.jobs.list(), ctx.previous);
      }
      toast.error("Failed to save job — please try again");
    },

    onSuccess: () => {
      toast.success("Job saved", { duration: 3000 });
      onSuccess?.();
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.list() });
    },
  });
}
