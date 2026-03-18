// useCostAnalytics.ts — Admin cost analytics hooks (FE-15.5)

import { useQuery } from "@tanstack/react-query";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { CostAnalytics, UserCostDetail } from "../types";

// ---------------------------------------------------------------------------
// useCostAnalyticsQuery — FE-15.5: GET /admin/costs/analytics
// ---------------------------------------------------------------------------

export function useCostAnalyticsQuery() {
  return useQuery<CostAnalytics, ApiError>({
    queryKey: queryKeys.admin.costAnalytics(),
    queryFn: () => apiClient.get<CostAnalytics>("/admin/costs/analytics"),
    staleTime: 5 * 60 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useUserCostDetail — FE-15.5: GET /admin/costs/users/{userId}
// ---------------------------------------------------------------------------

export function useUserCostDetail(userId: string | null) {
  return useQuery<UserCostDetail, ApiError>({
    queryKey: queryKeys.admin.userCosts(userId ?? ""),
    queryFn: () => apiClient.get<UserCostDetail>(`/admin/costs/users/${userId}`),
    enabled: !!userId,
    staleTime: 5 * 60 * 1000,
  });
}
