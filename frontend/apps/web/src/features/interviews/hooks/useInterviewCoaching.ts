// useInterviewCoaching.ts — hook for AI coaching session (FE-11.3)

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError } from "@reqruit/api-client";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { useStreamStore } from "@/features/applications/store/stream-store";

interface CoachingStartResponse {
  thread_id: string;
}

interface CoachingSections {
  strengths: string;
  areasToImprove: string;
  reframeSuggestion: string;
}

export function useInterviewCoaching() {
  const decrementCredit = useCreditsStore((s) => s.decrementCredit);
  const incrementCredit = useCreditsStore((s) => s.incrementCredit);
  const setActiveThread = useStreamStore((s) => s.setActiveThread);
  const resetStream = useStreamStore((s) => s.reset);
  const streamingBuffer = useStreamStore((s) => s.streamingBuffer);
  const isComplete = useStreamStore((s) => s.isComplete);

  const [sections, setSections] = React.useState<CoachingSections>({
    strengths: "",
    areasToImprove: "",
    reframeSuggestion: "",
  });

  // Parse streaming buffer into sections based on markdown headers
  React.useEffect(() => {
    if (!streamingBuffer) return;

    const parts = streamingBuffer.split(/^## /m).filter(Boolean);
    const parsed: CoachingSections = { strengths: "", areasToImprove: "", reframeSuggestion: "" };

    for (const part of parts) {
      if (part.startsWith("Strengths")) {
        parsed.strengths = part.replace(/^Strengths\n?/, "").trim();
      } else if (part.startsWith("Areas to improve")) {
        parsed.areasToImprove = part.replace(/^Areas to improve\n?/, "").trim();
      } else if (part.startsWith("Reframe suggestion")) {
        parsed.reframeSuggestion = part.replace(/^Reframe suggestion\n?/, "").trim();
      }
    }

    setSections(parsed);
  }, [streamingBuffer]);

  const startMutation = useMutation<CoachingStartResponse, ApiError, { questionId: string; answer: string }>({
    mutationFn: (payload) =>
      apiClient.post<CoachingStartResponse>("/interview/coaching", payload),

    onMutate: () => {
      decrementCredit();
      resetStream();
      setSections({ strengths: "", areasToImprove: "", reframeSuggestion: "" });
    },

    onSuccess: (data) => {
      setActiveThread(data.thread_id);
    },

    onError: () => {
      incrementCredit();
      toast.error("Failed to start coaching — please try again");
    },
  });

  const reset = React.useCallback(() => {
    resetStream();
    setSections({ strengths: "", areasToImprove: "", reframeSuggestion: "" });
  }, [resetStream]);

  return {
    startCoaching: startMutation.mutate,
    isPending: startMutation.isPending,
    isStreaming: !isComplete && !!useStreamStore.getState().activeThreadId,
    isComplete,
    sections,
    reset,
  };
}
