// offers-store.ts — Zustand store for negotiation streaming state (FE-12.4)

import { create } from "zustand";
import type { NegotiationSections } from "../types";

interface OffersState {
  activeOfferId: string | null;
  negotiationSections: NegotiationSections;
  negotiationPhase: "idle" | "streaming" | "complete";
}

interface OffersActions {
  setActiveOfferId: (id: string | null) => void;
  setNegotiationSections: (sections: NegotiationSections) => void;
  setNegotiationPhase: (phase: OffersState["negotiationPhase"]) => void;
  reset: () => void;
}

const initialState: OffersState = {
  activeOfferId: null,
  negotiationSections: {
    strategy: "",
    conversationScript: "",
    emailDraft: "",
  },
  negotiationPhase: "idle",
};

export const useOffersStore = create<OffersState & OffersActions>((set) => ({
  ...initialState,

  setActiveOfferId: (id) => set({ activeOfferId: id }),

  setNegotiationSections: (sections) => set({ negotiationSections: sections }),

  setNegotiationPhase: (phase) => set({ negotiationPhase: phase }),

  reset: () => set(initialState),
}));
