// Offer types for FE-12: Offer Analysis & Negotiation

export interface CompensationComponent {
  name: string;
  value: number;
  confidence: "high" | "medium" | "low";
  confidenceReason?: string;
}

export interface ParsedOffer {
  id: string;
  baseSalary: CompensationComponent;
  variable: CompensationComponent;
  equity: CompensationComponent;
  benefits: CompensationComponent;
  signingBonus: CompensationComponent;
  totalCompensation: number;
  rawText: string;
  createdAt: string;
}

export interface MarketPosition {
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  userPercentile: number;
  role: string;
  city: string;
}

export interface OfferComparison {
  offers: ParsedOffer[];
}

export interface NegotiationConfig {
  targetSalary: number;
  constraints: string;
  competingOffers?: string;
}

export interface NegotiationSections {
  strategy: string;
  conversationScript: string;
  emailDraft: string;
}

export type OfferOutcome = "accepted" | "rejected" | "withdrawn";

export interface OfferWithExpiry extends ParsedOffer {
  expiryDate?: string;
  outcome?: OfferOutcome;
  retrospectiveNotes?: string;
}
