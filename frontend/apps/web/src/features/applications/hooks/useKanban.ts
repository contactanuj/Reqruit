// useKanban.ts — Kanban board data hooks (FE-6.1, FE-6.3, FE-6.5)

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { Application, ApplicationNote, ApplicationStatsData } from "../types";

// ---------------------------------------------------------------------------
// useKanbanApplications — FE-6.1: GET /applications?view=kanban
// ---------------------------------------------------------------------------

export function useKanbanApplications() {
  return useQuery<Application[], ApiError>({
    queryKey: queryKeys.applications.list(),
    queryFn: () => apiClient.get<Application[]>("/applications?view=kanban"),
    staleTime: 30 * 1000, // 30 seconds (NFR-R4 Kanban)
    gcTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: true,
  });
}

// ---------------------------------------------------------------------------
// useApplicationNotes — FE-6.3: GET /applications/{id}/notes
// ---------------------------------------------------------------------------

export function useApplicationNotes(applicationId: string) {
  return useQuery<ApplicationNote[], ApiError>({
    queryKey: queryKeys.applications.notes(applicationId),
    queryFn: () => apiClient.get<ApplicationNote[]>(`/applications/${applicationId}/notes`),
    enabled: !!applicationId,
    staleTime: 60 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useAddNote — FE-6.3: POST /applications/{id}/notes
// ---------------------------------------------------------------------------

export function useAddNote(applicationId: string) {
  const queryClient = useQueryClient();

  return useMutation<ApplicationNote, ApiError, { content: string }>({
    mutationFn: (payload) =>
      apiClient.post<ApplicationNote>(`/applications/${applicationId}/notes`, payload),

    onMutate: async ({ content }) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.applications.notes(applicationId),
      });

      const previous = queryClient.getQueryData<ApplicationNote[]>(
        queryKeys.applications.notes(applicationId)
      );

      // Optimistic note
      const optimisticNote: ApplicationNote = {
        id: `optimistic-${Date.now()}`,
        application_id: applicationId,
        content,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      if (previous) {
        queryClient.setQueryData<ApplicationNote[]>(
          queryKeys.applications.notes(applicationId),
          [...previous, optimisticNote]
        );
      }

      return { previous };
    },

    onError: (_error, _payload, context) => {
      const ctx = context as { previous?: ApplicationNote[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<ApplicationNote[]>(
          queryKeys.applications.notes(applicationId),
          ctx.previous
        );
      }
      toast.error("Failed to save note — please try again");
    },

    onSuccess: () => {
      toast.success("Note saved", { duration: 3000 });
    },

    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.applications.notes(applicationId),
      });
    },
  });
}

// ---------------------------------------------------------------------------
// useUpdateNote — FE-6.3: PATCH /applications/{id}/notes/{note_id}
// ---------------------------------------------------------------------------

export function useUpdateNote(applicationId: string) {
  const queryClient = useQueryClient();

  return useMutation<ApplicationNote, ApiError, { noteId: string; content: string }>({
    mutationFn: ({ noteId, content }) =>
      apiClient.patch<ApplicationNote>(
        `/applications/${applicationId}/notes/${noteId}`,
        { content }
      ),

    onMutate: async ({ noteId, content }) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.applications.notes(applicationId),
      });

      const previous = queryClient.getQueryData<ApplicationNote[]>(
        queryKeys.applications.notes(applicationId)
      );

      if (previous) {
        queryClient.setQueryData<ApplicationNote[]>(
          queryKeys.applications.notes(applicationId),
          previous.map((note) =>
            note.id === noteId
              ? { ...note, content, updated_at: new Date().toISOString() }
              : note
          )
        );
      }

      return { previous };
    },

    onSuccess: () => {
      toast.success("Note updated", { duration: 3000 });
    },

    onError: (_error, _payload, context) => {
      const ctx = context as { previous?: ApplicationNote[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<ApplicationNote[]>(
          queryKeys.applications.notes(applicationId),
          ctx.previous
        );
      }
      toast.error("Failed to update note — please try again");
    },

    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.applications.notes(applicationId),
      });
    },
  });
}

// ---------------------------------------------------------------------------
// useApplicationStats — FE-6.5: GET /applications/stats
// ---------------------------------------------------------------------------

export function useApplicationStats() {
  return useQuery<ApplicationStatsData, ApiError>({
    queryKey: queryKeys.applications.stats(),
    queryFn: () => apiClient.get<ApplicationStatsData>("/applications/stats"),
    staleTime: 5 * 60 * 1000,
  });
}
