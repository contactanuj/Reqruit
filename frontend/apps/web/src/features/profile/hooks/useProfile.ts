// useProfile.ts — Profile hooks (FE-4.2, FE-4.3, FE-4.4, FE-4.5)

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type {
  Profile,
  ResumeStatusResponse,
  ResumeVersion,
  UpdateProfilePayload,
} from "../types";

// ---------------------------------------------------------------------------
// useResumeParseStatus — FE-4.2: polls /resumes/{id}/status
// ---------------------------------------------------------------------------

export function useResumeParseStatus(resumeId: string) {
  return useQuery<ResumeStatusResponse, ApiError>({
    queryKey: queryKeys.profile.resumeStatus(resumeId),
    queryFn: () => apiClient.get<ResumeStatusResponse>(`/resumes/${resumeId}/status`),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 2000;
    },
    refetchOnWindowFocus: true,
  });
}

// ---------------------------------------------------------------------------
// useProfileData — FE-4.3: GET /users/me/profile
// ---------------------------------------------------------------------------

export function useProfileData() {
  return useQuery<Profile, ApiError>({
    queryKey: queryKeys.profile.me(),
    queryFn: () => apiClient.get<Profile>("/users/me/profile"),
    staleTime: 60 * 60 * 1000, // 1 hour (NFR-R4)
    gcTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

// ---------------------------------------------------------------------------
// useUpdateProfile — FE-4.4: PATCH /users/me/profile (optimistic update)
// ---------------------------------------------------------------------------

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation<Profile, ApiError, UpdateProfilePayload>({
    mutationFn: (payload) => apiClient.patch<Profile>("/users/me/profile", payload),

    onMutate: async (payload) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.profile.me() });
      // Snapshot current data
      const previous = queryClient.getQueryData<Profile>(queryKeys.profile.me());
      // Optimistic update
      if (previous) {
        queryClient.setQueryData<Profile>(queryKeys.profile.me(), {
          ...previous,
          ...payload,
        });
      }
      return { previous };
    },

    onError: (_error, _payload, context) => {
      // Revert on error
      const ctx = context as { previous?: Profile } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<Profile>(queryKeys.profile.me(), ctx.previous);
      }
      // Don't toast here — the component handles errors with more specific messaging
    },

    onSuccess: () => {
      toast.success("Profile updated", { duration: 3000 });
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.profile.me() });
    },
  });
}

// ---------------------------------------------------------------------------
// useResumeList — FE-4.5: GET /resumes
// ---------------------------------------------------------------------------

export function useResumeList() {
  return useQuery<ResumeVersion[], ApiError>({
    queryKey: queryKeys.profile.resumes(),
    queryFn: () => apiClient.get<ResumeVersion[]>("/resumes"),
  });
}

// ---------------------------------------------------------------------------
// useSetMasterResume — FE-4.5: PATCH /resumes/{id} { is_master: true }
// ---------------------------------------------------------------------------

export function useSetMasterResume() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, string>({
    mutationFn: (resumeId) => apiClient.patch<void>(`/resumes/${resumeId}`, { is_master: true }),

    onMutate: async (resumeId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.profile.resumes() });
      const previous = queryClient.getQueryData<ResumeVersion[]>(queryKeys.profile.resumes());
      // Optimistic: swap master badge
      if (previous) {
        queryClient.setQueryData<ResumeVersion[]>(
          queryKeys.profile.resumes(),
          previous.map((r) => ({ ...r, isMaster: r.id === resumeId }))
        );
      }
      return { previous };
    },

    onError: (_error, _resumeId, context) => {
      const ctx = context as { previous?: ResumeVersion[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<ResumeVersion[]>(queryKeys.profile.resumes(), ctx.previous);
      }
      toast.error("Failed to set master resume — please try again");
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.profile.resumes() });
    },
  });
}

// ---------------------------------------------------------------------------
// useDeleteResume — FE-4.5: DELETE /resumes/{id}
// ---------------------------------------------------------------------------

export function useDeleteResume() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, string>({
    mutationFn: (resumeId) => apiClient.delete<void>(`/resumes/${resumeId}`),

    onMutate: async (resumeId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.profile.resumes() });
      const previous = queryClient.getQueryData<ResumeVersion[]>(queryKeys.profile.resumes());
      // Optimistic remove
      if (previous) {
        queryClient.setQueryData<ResumeVersion[]>(
          queryKeys.profile.resumes(),
          previous.filter((r) => r.id !== resumeId)
        );
      }
      return { previous };
    },

    onError: (_error, _resumeId, context) => {
      const ctx = context as { previous?: ResumeVersion[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<ResumeVersion[]>(queryKeys.profile.resumes(), ctx.previous);
      }
      toast.error("Failed to delete resume — please try again");
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.profile.resumes() });
    },
  });
}
