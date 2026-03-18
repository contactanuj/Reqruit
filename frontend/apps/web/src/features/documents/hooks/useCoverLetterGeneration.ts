// useCoverLetterGeneration.ts — hooks for AI cover letter generation workflow
// FE-7.1: initiate generation
// FE-7.4: approve and revise
// FE-7.5: version management

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import { usePWA } from "@repo/ui/hooks/use-pwa";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { useStreamStore } from "@/features/applications/store/stream-store";
import { useOnboardingStore } from "@/features/onboarding/store/onboarding-store";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface GenerateResponse {
  thread_id: string;
}

export interface CoverLetterVersion {
  id: string;
  version_number: number;
  generated_at: string;
  is_approved: boolean;
  content: string;
}

export interface ApproveResponse {
  id: string;
  is_approved: boolean;
}

export interface ReviseResponse {
  thread_id: string;
}

// ---------------------------------------------------------------------------
// useCoverLetterGeneration — FE-7.1
// ---------------------------------------------------------------------------

export function useCoverLetterGeneration(applicationId: string) {
  const decrementCredit = useCreditsStore((s) => s.decrementCredit);
  const incrementCredit = useCreditsStore((s) => s.incrementCredit);
  const setActiveThread = useStreamStore((s) => s.setActiveThread);
  const resetStream = useStreamStore((s) => s.reset);

  return useMutation<GenerateResponse, ApiError, void>({
    mutationFn: () =>
      apiClient.post<GenerateResponse>(
        `/applications/${applicationId}/cover-letter/generate`,
        {}
      ),

    onMutate: () => {
      // Optimistic credit decrement (ARCH-21)
      decrementCredit();
      resetStream();
    },

    onSuccess: (data) => {
      setActiveThread(data.thread_id);
    },

    onError: () => {
      // Revert optimistic decrement
      incrementCredit();
      toast.error("Failed to start cover letter generation — please try again");
    },
  });
}

// ---------------------------------------------------------------------------
// useApproveCoverLetter — FE-7.4
// ---------------------------------------------------------------------------

export function useApproveCoverLetter(applicationId: string) {
  const queryClient = useQueryClient();
  const hasApprovedFirstCoverLetter = useOnboardingStore(
    (s) => s.hasApprovedFirstCoverLetter,
  );
  const setHasApprovedFirstCoverLetter = useOnboardingStore(
    (s) => s.setHasApprovedFirstCoverLetter,
  );
  const { promptInstall } = usePWA();

  return useMutation<ApproveResponse, ApiError, void>({
    mutationFn: () =>
      apiClient.post<ApproveResponse>(
        `/applications/${applicationId}/cover-letter/approve`,
        {}
      ),

    onSuccess: () => {
      // Invalidate applications list to refresh "Cover Letter ✓" badge.
      // Note: uses applications.list() (not kanban()) because kanban is not
      // a separate query key — the kanban view reads from the same list query.
      void queryClient.invalidateQueries({
        queryKey: queryKeys.applications.list(),
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.documents.coverLetters(applicationId),
      });

      // Prompt PWA install on first cover letter approval (UX-15)
      if (!hasApprovedFirstCoverLetter) {
        setHasApprovedFirstCoverLetter(true);
        void promptInstall();
      }
    },

    onError: () => {
      toast.error("Failed to approve cover letter — please try again");
    },
  });
}

// ---------------------------------------------------------------------------
// useReviseCoverLetter — FE-7.4
// ---------------------------------------------------------------------------

export function useReviseCoverLetter(applicationId: string) {
  const setActiveThread = useStreamStore((s) => s.setActiveThread);
  const resetStream = useStreamStore((s) => s.reset);

  return useMutation<ReviseResponse, ApiError, { feedback: string }>({
    mutationFn: (payload) =>
      apiClient.post<ReviseResponse>(
        `/applications/${applicationId}/cover-letter/revise`,
        payload
      ),

    onMutate: () => {
      resetStream();
    },

    onSuccess: (data) => {
      setActiveThread(data.thread_id);
    },

    onError: () => {
      toast.error("Failed to submit revision — please try again");
    },
  });
}

// ---------------------------------------------------------------------------
// useCoverLetterVersions — FE-7.5
// ---------------------------------------------------------------------------

export function useCoverLetterVersions(applicationId: string) {
  return useQuery<CoverLetterVersion[], ApiError>({
    queryKey: queryKeys.documents.coverLetters(applicationId),
    queryFn: () =>
      apiClient.get<CoverLetterVersion[]>(
        `/applications/${applicationId}/cover-letters`
      ),
    enabled: !!applicationId,
    staleTime: 30 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useDeleteCoverLetterVersion — FE-7.5
// ---------------------------------------------------------------------------

export function useDeleteCoverLetterVersion(applicationId: string) {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, string>({
    mutationFn: (versionId) =>
      apiClient.delete<void>(
        `/applications/${applicationId}/cover-letters/${versionId}`
      ),

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.documents.coverLetters(applicationId),
      });
      toast.success("Version deleted");
    },

    onError: () => {
      toast.error("Failed to delete version — please try again");
    },
  });
}
