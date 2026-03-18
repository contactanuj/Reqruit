// useTaskQueue.ts — Admin task queue hooks (FE-15.3)

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { BackgroundTask } from "../types";

// ---------------------------------------------------------------------------
// useTaskQueueQuery — FE-15.3: GET /admin/tasks
// ---------------------------------------------------------------------------

export function useTaskQueueQuery() {
  return useQuery<BackgroundTask[], ApiError>({
    queryKey: queryKeys.admin.tasks(),
    queryFn: () => apiClient.get<BackgroundTask[]>("/admin/tasks"),
    staleTime: 30 * 1000,
    refetchOnWindowFocus: true,
  });
}

// ---------------------------------------------------------------------------
// useTaskLogs — FE-15.3: GET /admin/tasks/{taskId}/logs
// ---------------------------------------------------------------------------

export function useTaskLogs(taskId: string | null) {
  return useQuery<string, ApiError>({
    queryKey: queryKeys.admin.taskLogs(taskId ?? ""),
    queryFn: () => apiClient.get<string>(`/admin/tasks/${taskId}/logs`),
    enabled: !!taskId,
    staleTime: 10 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useRetryTask — FE-15.3: POST /admin/tasks/{id}/retry
// ---------------------------------------------------------------------------

export function useRetryTask() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, { id: string }>({
    mutationFn: ({ id }) =>
      apiClient.post<void>(`/admin/tasks/${id}/retry`, {}),

    onMutate: async ({ id }) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.admin.tasks(),
      });

      const previous = queryClient.getQueryData<BackgroundTask[]>(
        queryKeys.admin.tasks(),
      );

      if (previous) {
        queryClient.setQueryData<BackgroundTask[]>(
          queryKeys.admin.tasks(),
          previous.map((task) =>
            task.id === id ? { ...task, status: "pending" as const } : task,
          ),
        );
      }

      return { previous };
    },

    onError: (_error, _payload, context) => {
      const ctx = context as { previous?: BackgroundTask[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<BackgroundTask[]>(
          queryKeys.admin.tasks(),
          ctx.previous,
        );
      }
      toast.error("Failed to retry task — please try again");
    },

    onSuccess: () => {
      toast.success("Task queued for retry", { duration: 3000 });
    },

    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.admin.tasks(),
      });
    },
  });
}

// ---------------------------------------------------------------------------
// useCancelTask — FE-15.3: DELETE /admin/tasks/{id}
// ---------------------------------------------------------------------------

export function useCancelTask() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, { id: string }>({
    mutationFn: ({ id }) =>
      apiClient.delete<void>(`/admin/tasks/${id}`),

    onMutate: async ({ id }) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.admin.tasks(),
      });

      const previous = queryClient.getQueryData<BackgroundTask[]>(
        queryKeys.admin.tasks(),
      );

      if (previous) {
        queryClient.setQueryData<BackgroundTask[]>(
          queryKeys.admin.tasks(),
          previous.filter((task) => task.id !== id),
        );
      }

      return { previous };
    },

    onError: (_error, _payload, context) => {
      const ctx = context as { previous?: BackgroundTask[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<BackgroundTask[]>(
          queryKeys.admin.tasks(),
          ctx.previous,
        );
      }
      toast.error("Failed to cancel task — please try again");
    },

    onSuccess: () => {
      toast.success("Task cancelled", { duration: 3000 });
    },

    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.admin.tasks(),
      });
    },
  });
}
