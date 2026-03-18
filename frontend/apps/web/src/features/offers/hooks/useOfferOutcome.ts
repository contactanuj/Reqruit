// useOfferOutcome.ts — FE-12.5: Record offer outcome and fetch expiry data

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { OfferOutcome, OfferWithExpiry } from "../types";

interface OutcomePayload {
  outcome: OfferOutcome;
  retrospectiveNotes?: string;
}

export function useOfferOutcome(offerId: string) {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, OutcomePayload>({
    mutationFn: (payload) =>
      apiClient.post(`/offers/${offerId}/outcome`, payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.offers.detail(offerId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.offers.all });
      toast.success("Offer outcome recorded");
    },

    onError: (error) => {
      toast.error(error.message || "Failed to record outcome — please try again");
    },
  });
}

export function useOfferExpiry(offerId: string | null) {
  return useQuery<OfferWithExpiry>({
    queryKey: queryKeys.offers.detail(offerId ?? ""),
    queryFn: () =>
      apiClient.get<OfferWithExpiry>(`/offers/${offerId}`),
    enabled: !!offerId,
    staleTime: 60_000, // 1 min — expiry is time-sensitive
  });
}
