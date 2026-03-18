// useOptimisticStatusMove.ts — Optimistic status mutation for Kanban (FE-6.1)
// Pattern: onMutate → cancel + snapshot + apply → onError → revert + toast → onSettled → invalidate

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { Application, ApplicationStatus } from "../types";

interface StatusMovePayload {
  applicationId: string;
  newStatus: ApplicationStatus;
  previousStatus: ApplicationStatus;
}

export function useOptimisticStatusMove() {
  const queryClient = useQueryClient();

  return useMutation<unknown, ApiError, StatusMovePayload, { previous: Application[] | undefined }>({
    mutationFn: ({ applicationId, newStatus }) =>
      apiClient.patch(`/applications/${applicationId}/status`, { status: newStatus }),

    onMutate: async ({ applicationId, newStatus }) => {
      // Cancel any in-flight refetches to avoid overwriting our optimistic update
      await queryClient.cancelQueries({ queryKey: queryKeys.applications.list() });

      // Snapshot current state for rollback
      const previous = queryClient.getQueryData<Application[]>(queryKeys.applications.list());

      // Optimistically update the cache — synchronous, visible in < 50ms (NFR-P7)
      if (previous) {
        queryClient.setQueryData<Application[]>(
          queryKeys.applications.list(),
          previous.map((app) =>
            app.id === applicationId ? { ...app, status: newStatus } : app
          )
        );
      }

      return { previous };
    },

    onError: (_error, _payload, context) => {
      // Revert to snapshot on failure
      if (context?.previous) {
        queryClient.setQueryData<Application[]>(
          queryKeys.applications.list(),
          context.previous
        );
      }
      toast.error("Failed to update — changes reverted");
    },

    onSettled: () => {
      // Always refetch to sync with server truth
      void queryClient.invalidateQueries({ queryKey: queryKeys.applications.list() });
    },
  });
}
