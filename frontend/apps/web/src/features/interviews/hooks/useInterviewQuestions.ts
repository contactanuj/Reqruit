// useInterviewQuestions.ts — hooks for AI behavioral questions (FE-11.2)

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import type { InterviewQuestion } from "../types";

export function useInterviewQuestionsQuery(applicationId: string) {
  return useQuery<InterviewQuestion[], ApiError>({
    queryKey: queryKeys.interview.questions(applicationId),
    queryFn: () =>
      apiClient.get<InterviewQuestion[]>(
        `/applications/${applicationId}/interview-questions`,
      ),
    enabled: !!applicationId,
  });
}

export function useGenerateQuestions(applicationId: string) {
  const queryClient = useQueryClient();
  const decrementCredit = useCreditsStore((s) => s.decrementCredit);
  const incrementCredit = useCreditsStore((s) => s.incrementCredit);

  return useMutation<InterviewQuestion[], ApiError, void>({
    mutationFn: () =>
      apiClient.post<InterviewQuestion[]>(
        `/applications/${applicationId}/interview-questions/generate`,
        {},
      ),

    onMutate: () => {
      decrementCredit();
    },

    onSuccess: (data) => {
      queryClient.setQueryData(
        queryKeys.interview.questions(applicationId),
        data,
      );
    },

    onError: () => {
      incrementCredit();
      toast.error("Failed to generate questions — please try again");
    },
  });
}
