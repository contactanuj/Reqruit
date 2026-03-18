// offers feature barrel export (FE-12)

// Components
export { OfferParseForm } from "./components/OfferParseForm";
export { CompensationBreakdown } from "./components/CompensationBreakdown";
export { MarketPositionChart } from "./components/MarketPositionChart";
export { OfferComparison } from "./components/OfferComparison";
export { NegotiationSetup } from "./components/NegotiationSetup";
export { NegotiationSession } from "./components/NegotiationSession";
export { OfferExpiryCountdown } from "./components/OfferExpiryCountdown";
export { OfferOutcomeForm } from "./components/OfferOutcomeForm";

// Hooks
export { useOfferParse } from "./hooks/useOfferParse";
export { useMarketPosition } from "./hooks/useMarketPosition";
export { useOfferComparison } from "./hooks/useOfferComparison";
export { useNegotiation } from "./hooks/useNegotiation";
export { useOfferOutcome, useOfferExpiry } from "./hooks/useOfferOutcome";

// Store
export { useOffersStore } from "./store/offers-store";

// Types
export type {
  CompensationComponent,
  ParsedOffer,
  MarketPosition,
  OfferComparison as OfferComparisonType,
  NegotiationConfig,
  NegotiationSections,
  OfferOutcome,
  OfferWithExpiry,
} from "./types";
