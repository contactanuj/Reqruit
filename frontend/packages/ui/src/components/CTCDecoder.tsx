// CTCDecoder.tsx — India CTC breakdown dialog (FE-5.8)
// Only shown for IN locale users (FR30).
// Focus trap + Escape close + aria labels for all currency values (UX-12, NFR-A6).

"use client";

import * as React from "react";
import { formatLPA } from "../lib/locale";
import type { LocaleCode } from "../lib/locale";
import { useFocusTrap } from "../hooks/use-focus-trap";

export interface CTCDecoderProps {
  /** Annual CTC minimum in rupees */
  salaryMin: number;
  /** Annual CTC maximum in rupees */
  salaryMax?: number;
  locale: LocaleCode;
  /** Whether the decoder dialog is open */
  open: boolean;
  /** Called to close the dialog */
  onClose: () => void;
}

/** Estimate in-hand monthly (rough: 70% of CTC after tax/PF) */
function estimateInHand(annual: number): { min: number; max: number } {
  const monthly = annual / 12;
  return {
    min: Math.round(monthly * 0.65),
    max: Math.round(monthly * 0.72),
  };
}

/** Spell out lakh amount for aria-label (UX-12) */
function spellLakhs(amountInRupees: number): string {
  const lakhs = amountInRupees / 100_000;
  if (lakhs >= 100) {
    const crores = lakhs / 100;
    return `${crores.toFixed(1)} crore rupees`;
  }
  return `${lakhs.toFixed(1)} lakh rupees`;
}

export function CTCDecoder({ salaryMin, salaryMax, locale, open, onClose }: CTCDecoderProps) {
  const { dialogRef, handleBackdropClick } = useFocusTrap({ open, onClose });

  if (!open) return null;

  const maxSalary = salaryMax ?? salaryMin;
  const inHand = estimateInHand(salaryMin);
  const inHandMax = estimateInHand(maxSalary);
  const variableMin = Math.round(salaryMin * 0.1);
  const variableMax = Math.round(maxSalary * 0.2);
  const noticeCost = Math.round(salaryMin / 12);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={handleBackdropClick}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-label="CTC Breakdown"
        aria-modal="true"
        className="relative w-full max-w-sm rounded-lg bg-background border border-border p-6 shadow-lg outline-none"
      >
        <button
          type="button"
          aria-label="Close CTC Breakdown"
          onClick={onClose}
          className="absolute top-3 right-3 text-muted-foreground hover:text-foreground"
        >
          ✕
        </button>

        <h2 className="mb-4 text-base font-semibold">CTC Breakdown</h2>

        {/* In-hand monthly estimate */}
        <div className="mb-3">
          <p className="text-xs text-muted-foreground mb-1">In-hand monthly estimate</p>
          <p
            className="font-mono text-sm font-semibold"
            aria-label={`In-hand monthly: ${spellLakhs(inHand.min)} to ${spellLakhs(inHandMax.max)} per month`}
          >
            {formatLPA(inHand.min, locale)} – {formatLPA(inHandMax.max, locale)} /mo
          </p>
          <p className="text-xs text-muted-foreground">(After estimated tax & PF deduction)</p>
        </div>

        {/* Variable component */}
        <div className="mb-3">
          <p className="text-xs text-muted-foreground mb-1">Variable component range</p>
          <p
            className="font-mono text-sm font-semibold"
            aria-label={`Variable: ${spellLakhs(variableMin)} to ${spellLakhs(variableMax)}`}
          >
            {formatLPA(variableMin, locale)} – {formatLPA(variableMax, locale)}
          </p>
          <p className="text-xs text-muted-foreground">(10–20% of CTC, bonus/ESOPs)</p>
        </div>

        {/* Notice buyout cost */}
        <div className="mb-3">
          <p className="text-xs text-muted-foreground mb-1">Notice buyout cost estimate</p>
          <p
            className="font-mono text-sm font-semibold"
            aria-label={`Notice buyout: ${spellLakhs(noticeCost)}`}
          >
            {formatLPA(noticeCost, locale)}
          </p>
          <p className="text-xs text-muted-foreground">(~1 month gross)</p>
        </div>

        {/* Market positioning */}
        <div>
          <p className="text-xs text-muted-foreground mb-1">Market positioning</p>
          <p className="text-sm font-semibold">
            {salaryMin >= 2_500_000
              ? "Top 10%"
              : salaryMin >= 1_500_000
              ? "Top 25%"
              : salaryMin >= 800_000
              ? "Median"
              : "Below median"}{" "}
            for role
          </p>
        </div>
      </div>
    </div>
  );
}
