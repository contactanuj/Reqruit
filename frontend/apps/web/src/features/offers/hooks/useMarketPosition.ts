// useMarketPosition.ts — FE-12.2: Fetch market position data for an offer

import { useQuery } from "@tanstack/react-query";
import { apiClient, queryKeys } from "@reqruit/api-client";
import type { MarketPosition } from "../types";

export function useMarketPosition(offerId: string | null) {
  return useQuery<MarketPosition>({
    queryKey: queryKeys.offers.detail(offerId ?? ""),
    queryFn: () =>
      apiClient.get<MarketPosition>(`/offers/${offerId}/market-position`),
    enabled: !!offerId,
    staleTime: 300_000, // 5 min — market data relatively stable
  });
}
