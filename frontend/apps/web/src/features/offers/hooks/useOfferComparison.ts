// useOfferComparison.ts — FE-12.3: Compare multiple offers side-by-side

import { useQuery } from "@tanstack/react-query";
import { apiClient, queryKeys } from "@reqruit/api-client";
import type { OfferComparison } from "../types";

export function useOfferComparison(offerIds: string[]) {
  return useQuery<OfferComparison>({
    queryKey: queryKeys.offers.comparison(offerIds),
    queryFn: () =>
      apiClient.get<OfferComparison>(
        `/offers/compare?ids=${offerIds.join(",")}`,
      ),
    enabled: offerIds.length >= 2,
    staleTime: 300_000,
  });
}
