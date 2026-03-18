"use client";

// OfferOutcomeForm.tsx — FE-12.5: Record offer outcome (accepted/rejected/withdrawn) with notes

import * as React from "react";
import DOMPurify from "dompurify";
import type { OfferOutcome } from "../types";

interface OfferOutcomeFormProps {
  offerId: string;
  onSubmit: (outcome: OfferOutcome, notes?: string) => void;
  isPending: boolean;
  currentOutcome?: OfferOutcome;
}

const outcomeOptions: { value: OfferOutcome; label: string; description: string }[] = [
  { value: "accepted", label: "Accepted", description: "You accepted this offer" },
  { value: "rejected", label: "Rejected", description: "You declined this offer" },
  { value: "withdrawn", label: "Withdrawn", description: "The employer withdrew the offer" },
];

export function OfferOutcomeForm({
  offerId,
  onSubmit,
  isPending,
  currentOutcome,
}: OfferOutcomeFormProps) {
  const [selectedOutcome, setSelectedOutcome] = React.useState<OfferOutcome | "">(
    currentOutcome ?? "",
  );
  const [notes, setNotes] = React.useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOutcome) return;
    const sanitizedNotes = notes.trim()
      ? DOMPurify.sanitize(notes.trim(), { ALLOWED_TAGS: [] })
      : undefined;
    onSubmit(selectedOutcome, sanitizedNotes);
  };

  return (
    <form
      data-testid="offer-outcome-form"
      onSubmit={handleSubmit}
      className="space-y-4"
    >
      <h3 className="text-base font-semibold text-foreground">
        Record Outcome
      </h3>

      {/* Outcome radio buttons */}
      <fieldset>
        <legend className="mb-2 text-sm font-medium text-foreground">
          What happened with this offer?
        </legend>
        <div
          className="space-y-2"
          role="radiogroup"
          aria-label="Offer outcome"
          data-testid="outcome-radio-group"
        >
          {outcomeOptions.map((option) => (
            <label
              key={option.value}
              className={`flex cursor-pointer items-start gap-3 rounded-md border px-4 py-3 transition-colors ${
                selectedOutcome === option.value
                  ? "border-primary bg-primary/5"
                  : "border-border hover:bg-muted/50"
              }`}
            >
              <input
                type="radio"
                name={`outcome-${offerId}`}
                value={option.value}
                checked={selectedOutcome === option.value}
                onChange={() => setSelectedOutcome(option.value)}
                className="mt-0.5 accent-primary"
                data-testid={`outcome-radio-${option.value}`}
              />
              <div>
                <span className="text-sm font-medium text-foreground">
                  {option.label}
                </span>
                <p className="text-xs text-muted-foreground">
                  {option.description}
                </p>
              </div>
            </label>
          ))}
        </div>
      </fieldset>

      {/* Retrospective notes */}
      <div>
        <label
          htmlFor="outcome-notes-input"
          className="mb-1 block text-sm font-medium text-foreground"
        >
          Retrospective notes{" "}
          <span className="text-muted-foreground">(optional)</span>
        </label>
        <textarea
          id="outcome-notes-input"
          data-testid="outcome-notes-input"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="What did you learn? What would you do differently?"
          rows={3}
          className="w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        />
      </div>

      {/* Submit */}
      <button
        type="submit"
        data-testid="submit-outcome-button"
        disabled={!selectedOutcome || isPending}
        className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isPending ? "Saving..." : "Record outcome"}
      </button>
    </form>
  );
}
