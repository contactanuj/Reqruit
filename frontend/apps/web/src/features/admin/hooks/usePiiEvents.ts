// usePiiEvents.ts — Admin PII events hooks (FE-15.4)

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { PiiEvent } from "../types";

// ---------------------------------------------------------------------------
// usePiiEventsQuery — FE-15.4: GET /admin/pii-events
// ---------------------------------------------------------------------------

export function usePiiEventsQuery() {
  return useQuery<PiiEvent[], ApiError>({
    queryKey: queryKeys.admin.piiEvents(),
    queryFn: () => apiClient.get<PiiEvent[]>("/admin/pii-events"),
    staleTime: 60 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useResolvePiiEvent — FE-15.4: PATCH /admin/pii-events/{id}
// ---------------------------------------------------------------------------

export function useResolvePiiEvent() {
  const queryClient = useQueryClient();

  return useMutation<
    PiiEvent,
    ApiError,
    { id: string; status: "confirmed" | "false_positive" }
  >({
    mutationFn: ({ id, status }) =>
      apiClient.patch<PiiEvent>(`/admin/pii-events/${id}`, { status }),

    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.admin.piiEvents(),
      });

      const previous = queryClient.getQueryData<PiiEvent[]>(
        queryKeys.admin.piiEvents(),
      );

      if (previous) {
        queryClient.setQueryData<PiiEvent[]>(
          queryKeys.admin.piiEvents(),
          previous.map((event) =>
            event.id === id ? { ...event, status } : event,
          ),
        );
      }

      return { previous };
    },

    onError: (_error, _payload, context) => {
      const ctx = context as { previous?: PiiEvent[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<PiiEvent[]>(
          queryKeys.admin.piiEvents(),
          ctx.previous,
        );
      }
      toast.error("Failed to resolve PII event — please try again");
    },

    onSuccess: () => {
      toast.success("PII event resolved", { duration: 3000 });
    },

    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.admin.piiEvents(),
      });
    },
  });
}
