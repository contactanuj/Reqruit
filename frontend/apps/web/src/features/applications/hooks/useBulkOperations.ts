// useBulkOperations.ts — Bulk delete, withdraw, and export mutations (FE-6.4)

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { Application } from "../types";
import { useApplicationsStore } from "../store/applications-store";

// ---------------------------------------------------------------------------
// useBulkDelete — DELETE /applications/bulk with selected IDs
// ---------------------------------------------------------------------------

export function useBulkDelete() {
  const queryClient = useQueryClient();
  const clearSelection = useApplicationsStore((s) => s.clearSelection);

  return useMutation<unknown, ApiError, string[]>({
    mutationFn: (ids) =>
      apiClient.delete(`/applications/bulk`, { data: { ids } }),

    onMutate: async (ids) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.applications.list() });
      const previous = queryClient.getQueryData<Application[]>(queryKeys.applications.list());

      // Optimistically remove cards
      if (previous) {
        queryClient.setQueryData<Application[]>(
          queryKeys.applications.list(),
          previous.filter((a) => !ids.includes(a.id))
        );
      }

      return { previous };
    },

    onError: (_error, _ids, context) => {
      const ctx = context as { previous?: Application[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<Application[]>(queryKeys.applications.list(), ctx.previous);
      }
      toast.error("Failed to delete applications — changes reverted");
    },

    onSuccess: () => {
      toast.success("Applications deleted");
      clearSelection();
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.applications.list() });
    },
  });
}

// ---------------------------------------------------------------------------
// useBulkWithdraw — Move all selected applications to Withdrawn
// ---------------------------------------------------------------------------

const TERMINAL_STATUSES = new Set(["Accepted", "Rejected", "Withdrawn"]);

export function useBulkWithdraw() {
  const queryClient = useQueryClient();
  const clearSelection = useApplicationsStore((s) => s.clearSelection);

  return useMutation<unknown, ApiError, string[]>({
    mutationFn: (ids) => {
      // Filter out applications already in terminal states
      const applications = queryClient.getQueryData<Application[]>(queryKeys.applications.list());
      const eligible = ids.filter((id) => {
        const app = applications?.find((a) => a.id === id);
        return app && !TERMINAL_STATUSES.has(app.status);
      });
      const skipped = ids.length - eligible.length;

      if (skipped > 0) {
        toast.info(
          `${skipped} application${skipped !== 1 ? "s" : ""} skipped (already in a terminal state)`
        );
      }

      if (eligible.length === 0) {
        return Promise.resolve();
      }

      return apiClient.patch(`/applications/bulk/status`, {
        ids: eligible,
        status: "Withdrawn",
      });
    },

    onMutate: async (ids) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.applications.list() });
      const previous = queryClient.getQueryData<Application[]>(queryKeys.applications.list());

      if (previous) {
        queryClient.setQueryData<Application[]>(
          queryKeys.applications.list(),
          previous.map((a) =>
            ids.includes(a.id) && !TERMINAL_STATUSES.has(a.status)
              ? { ...a, status: "Withdrawn" as const }
              : a
          )
        );
      }

      return { previous };
    },

    onError: (_error, _ids, context) => {
      const ctx = context as { previous?: Application[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<Application[]>(queryKeys.applications.list(), ctx.previous);
      }
      toast.error("Failed to withdraw applications — changes reverted");
    },

    onSuccess: () => {
      toast.success("Applications withdrawn");
      clearSelection();
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.applications.list() });
    },
  });
}

// ---------------------------------------------------------------------------
// useBulkExport — GET /applications/export?ids=... → CSV download
// ---------------------------------------------------------------------------

export function useBulkExport() {
  return useMutation<void, ApiError, string[]>({
    mutationFn: async (ids) => {
      const queryString = ids.map((id) => `ids=${encodeURIComponent(id)}`).join("&");
      const res = await apiClient.get(`/applications/export?${queryString}`, { responseType: 'blob' });
      const blob = res instanceof Blob ? res : new Blob([res as BlobPart]);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "applications.csv";
      a.click();
      URL.revokeObjectURL(url);
    },

    onError: () => {
      toast.error("Failed to export applications");
    },

    onSuccess: () => {
      toast.success("Export started — check your downloads");
    },
  });
}
