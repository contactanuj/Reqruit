// useNegotiation.ts — FE-12.4: AI negotiation strategy generation (SSE streaming)

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError } from "@reqruit/api-client";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { useStreamStore } from "@/features/applications/store/stream-store";
import { useOffersStore } from "../store/offers-store";
import type { NegotiationConfig, NegotiationSections } from "../types";

interface NegotiationStartResponse {
  thread_id: string;
}

export function useNegotiation(offerId: string) {
  const decrementCredit = useCreditsStore((s) => s.decrementCredit);
  const incrementCredit = useCreditsStore((s) => s.incrementCredit);
  const setActiveThread = useStreamStore((s) => s.setActiveThread);
  const resetStream = useStreamStore((s) => s.reset);
  const streamingBuffer = useStreamStore((s) => s.streamingBuffer);
  const isComplete = useStreamStore((s) => s.isComplete);
  const activeThreadId = useStreamStore((s) => s.activeThreadId);

  const setActiveOfferId = useOffersStore((s) => s.setActiveOfferId);
  const setNegotiationSections = useOffersStore((s) => s.setNegotiationSections);
  const setNegotiationPhase = useOffersStore((s) => s.setNegotiationPhase);

  const [sections, setSections] = React.useState<NegotiationSections>({
    strategy: "",
    conversationScript: "",
    emailDraft: "",
  });

  // Parse streaming buffer into sections based on markdown headers
  React.useEffect(() => {
    if (!streamingBuffer) return;

    const parts = streamingBuffer.split(/^## /m).filter(Boolean);
    const parsed: NegotiationSections = {
      strategy: "",
      conversationScript: "",
      emailDraft: "",
    };

    for (const part of parts) {
      if (part.startsWith("Strategy")) {
        parsed.strategy = part.replace(/^Strategy\n?/, "").trim();
      } else if (part.startsWith("Conversation Script")) {
        parsed.conversationScript = part
          .replace(/^Conversation Script\n?/, "")
          .trim();
      } else if (part.startsWith("Email Draft")) {
        parsed.emailDraft = part.replace(/^Email Draft\n?/, "").trim();
      }
    }

    setSections(parsed);
    setNegotiationSections(parsed);
  }, [streamingBuffer, setNegotiationSections]);

  // Track negotiation phase in store
  React.useEffect(() => {
    if (isComplete) {
      setNegotiationPhase("complete");
    }
  }, [isComplete, setNegotiationPhase]);

  const startMutation = useMutation<
    NegotiationStartResponse,
    ApiError,
    NegotiationConfig
  >({
    mutationFn: (payload) =>
      apiClient.post<NegotiationStartResponse>(
        `/offers/${offerId}/negotiate`,
        payload,
      ),

    onMutate: () => {
      decrementCredit();
      resetStream();
      setActiveOfferId(offerId);
      setNegotiationPhase("streaming");
      setSections({ strategy: "", conversationScript: "", emailDraft: "" });
    },

    onSuccess: (data) => {
      setActiveThread(data.thread_id);
    },

    onError: () => {
      incrementCredit();
      setNegotiationPhase("idle");
      toast.error("Failed to start negotiation advisor — please try again");
    },
  });

  const reset = React.useCallback(() => {
    resetStream();
    setNegotiationPhase("idle");
    setActiveOfferId(null);
    setSections({ strategy: "", conversationScript: "", emailDraft: "" });
    setNegotiationSections({ strategy: "", conversationScript: "", emailDraft: "" });
  }, [resetStream, setNegotiationPhase, setActiveOfferId, setNegotiationSections]);

  return {
    startNegotiation: startMutation.mutate,
    isPending: startMutation.isPending,
    isStreaming: !isComplete && !!activeThreadId,
    isComplete,
    sections,
    reset,
  };
}
