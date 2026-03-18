"use client";

// OfferParseForm.tsx — FE-12.1: Paste offer letter text and parse it
// Textarea for pasting offer letter, "Parse offer" button, loading skeleton.

import * as React from "react";
import { useOfferParse } from "../hooks/useOfferParse";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import type { ParsedOffer } from "../types";

interface OfferParseFormProps {
  onParsed?: (offer: ParsedOffer) => void;
}

export function OfferParseForm({ onParsed }: OfferParseFormProps) {
  const [text, setText] = React.useState("");
  const { mutate: parseOffer, isPending } = useOfferParse();
  const dailyCredits = useCreditsStore((s) => s.dailyCredits);
  const hasCredits = dailyCredits >= 1;

  const handleParse = () => {
    if (!text.trim() || !hasCredits) return;
    parseOffer(
      { text: text.trim() },
      {
        onSuccess: (data) => {
          onParsed?.(data);
        },
      },
    );
  };

  return (
    <div data-testid="offer-parse-form" className="flex flex-col gap-4">
      <div>
        <label
          htmlFor="offer-text-input"
          className="mb-1 block text-sm font-medium text-foreground"
        >
          Paste your offer letter
        </label>
        <textarea
          id="offer-text-input"
          data-testid="offer-text-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste the full offer letter or compensation details here..."
          rows={10}
          className="w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        />
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          data-testid="parse-offer-button"
          disabled={!text.trim() || !hasCredits || isPending}
          onClick={handleParse}
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPending ? "Parsing..." : "Parse offer"}
        </button>
        {!hasCredits && (
          <span
            data-testid="no-credits-message"
            className="text-sm text-muted-foreground"
          >
            Insufficient credits ({dailyCredits} remaining)
          </span>
        )}
      </div>

      {/* Loading skeleton */}
      {isPending && (
        <div data-testid="parse-loading-skeleton" className="space-y-3">
          <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
          <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
          <div className="h-4 w-1/3 animate-pulse rounded bg-muted" />
        </div>
      )}
    </div>
  );
}
