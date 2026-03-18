// useOfferParse.ts — FE-12.1: Parse offer letter text into structured compensation data

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import type { ParsedOffer } from "../types";

interface OfferParsePayload {
  text: string;
}

export function useOfferParse() {
  const queryClient = useQueryClient();
  const decrementCredit = useCreditsStore((s) => s.decrementCredit);
  const incrementCredit = useCreditsStore((s) => s.incrementCredit);

  return useMutation<ParsedOffer, ApiError, OfferParsePayload>({
    mutationFn: (payload) =>
      apiClient.post<ParsedOffer>("/offers/parse", payload),

    onMutate: () => {
      decrementCredit();
    },

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.offers.all });
      toast.success("Offer parsed successfully");
    },

    onError: (error) => {
      incrementCredit();
      toast.error(
        error.message || "Failed to parse offer — please try again",
      );
    },
  });
}
