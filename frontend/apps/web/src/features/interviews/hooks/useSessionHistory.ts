// useSessionHistory.ts — hook for mock interview session history (FE-11.5)

import { useQuery } from "@tanstack/react-query";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { SessionSummary } from "../types";

export function useSessionHistoryQuery() {
  return useQuery<SessionSummary[], ApiError>({
    queryKey: queryKeys.interview.mockSessions(),
    queryFn: () =>
      apiClient.get<SessionSummary[]>("/interview/mock-sessions"),
  });
}
