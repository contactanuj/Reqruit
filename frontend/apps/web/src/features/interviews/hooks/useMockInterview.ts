// useMockInterview.ts — hooks for mock interview sessions (FE-11.4)

import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError } from "@reqruit/api-client";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { useStreamStore } from "@/features/applications/store/stream-store";
import { useInterviewStore } from "../store/interview-store";
import type { MockSessionConfig } from "../types";

interface StartSessionResponse {
  session_id: string;
  thread_id: string;
  total_questions: number;
}

interface SubmitAnswerResponse {
  thread_id: string;
  is_last: boolean;
}

export function useStartSession() {
  const decrementCredit = useCreditsStore((s) => s.decrementCredit);
  const incrementCredit = useCreditsStore((s) => s.incrementCredit);
  const setActiveThread = useStreamStore((s) => s.setActiveThread);
  const resetStream = useStreamStore((s) => s.reset);
  const startSession = useInterviewStore((s) => s.startSession);
  const setTotalQuestions = useInterviewStore((s) => s.setTotalQuestions);

  return useMutation<StartSessionResponse, ApiError, MockSessionConfig>({
    mutationFn: (config) =>
      apiClient.post<StartSessionResponse>("/interview/mock-sessions", config),

    onMutate: () => {
      decrementCredit();
      resetStream();
    },

    onSuccess: (data, config) => {
      startSession(data.session_id, config);
      setTotalQuestions(data.total_questions);
      setActiveThread(data.thread_id);
    },

    onError: () => {
      incrementCredit();
      toast.error("Failed to start mock interview — please try again");
    },
  });
}

export function useSubmitAnswer(sessionId: string | null) {
  const setActiveThread = useStreamStore((s) => s.setActiveThread);
  const resetStream = useStreamStore((s) => s.reset);
  const recordAnswer = useInterviewStore((s) => s.recordAnswer);
  const advanceQuestion = useInterviewStore((s) => s.advanceQuestion);

  return useMutation<SubmitAnswerResponse, ApiError, { answer: string }>({
    mutationFn: (payload) =>
      apiClient.post<SubmitAnswerResponse>(
        `/interview/mock-sessions/${sessionId}/answer`,
        payload,
      ),

    onMutate: ({ answer }) => {
      recordAnswer(answer);
      resetStream();
    },

    onSuccess: (data) => {
      setActiveThread(data.thread_id);
      if (data.is_last) {
        advanceQuestion();
      }
    },

    onError: () => {
      toast.error("Failed to submit answer — please try again");
    },
  });
}
