// useTranscript.ts — hook for mock interview transcript & ratings (FE-11.5)

import { useQuery } from "@tanstack/react-query";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { TranscriptData } from "../types";

export function useTranscriptQuery(sessionId: string | null) {
  return useQuery<TranscriptData, ApiError>({
    queryKey: queryKeys.interview.transcript(sessionId!),
    queryFn: () =>
      apiClient.get<TranscriptData>(
        `/interview/mock-sessions/${sessionId}/transcript`,
      ),
    enabled: !!sessionId,
  });
}
