"use client";

// CompensationBreakdown.tsx — FE-12.1: Parsed compensation components with confidence indicators
// Uses CSS group/group-hover for tooltip pattern (no Radix UI).

import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import DOMPurify from "dompurify";
import { formatLPA } from "@repo/ui/lib/locale";
import { useLocale } from "@repo/ui/hooks";
import type { ParsedOffer, CompensationComponent } from "../types";

interface CompensationBreakdownProps {
  offer: ParsedOffer;
}

interface CompensationRowProps {
  component: CompensationComponent;
  formatValue: (amount: number) => string;
}

// ---------------------------------------------------------------------------
// Confidence badge colors
// ---------------------------------------------------------------------------

const confidenceColors: Record<CompensationComponent["confidence"], string> = {
  high: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  medium:
    "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  low: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
};

// ---------------------------------------------------------------------------
// Sub-component: single compensation row
// ---------------------------------------------------------------------------

function CompensationRow({
  component,
  formatValue,
}: CompensationRowProps) {
  const slug = component.name.toLowerCase().replace(/\s+/g, "-");

  return (
    <div
      data-testid={`compensation-row-${slug}`}
      className="flex items-center justify-between rounded-md border border-border px-4 py-3"
    >
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-foreground">
          {DOMPurify.sanitize(component.name)}
        </span>

        {/* Confidence indicator with Radix Tooltip for keyboard accessibility */}
        <TooltipPrimitive.Provider>
          <TooltipPrimitive.Root>
            <TooltipPrimitive.Trigger asChild>
              <span
                data-testid={`confidence-badge-${slug}`}
                className={`inline-flex cursor-default items-center rounded-full px-2 py-0.5 text-xs font-medium ${confidenceColors[component.confidence]}`}
                tabIndex={0}
              >
                {component.confidence}
              </span>
            </TooltipPrimitive.Trigger>
            {component.confidenceReason && (
              <TooltipPrimitive.Portal>
                <TooltipPrimitive.Content
                  data-testid={`confidence-tooltip-${slug}`}
                  side="top"
                  sideOffset={4}
                  className="z-50 max-w-xs whitespace-normal rounded-md bg-foreground px-3 py-1.5 text-xs text-background shadow-md animate-in fade-in-0 zoom-in-95"
                >
                  {DOMPurify.sanitize(component.confidenceReason)}
                  <TooltipPrimitive.Arrow className="fill-foreground" />
                </TooltipPrimitive.Content>
              </TooltipPrimitive.Portal>
            )}
          </TooltipPrimitive.Root>
        </TooltipPrimitive.Provider>
      </div>

      <span
        data-testid={`compensation-value-${slug}`}
        className="text-sm font-semibold tabular-nums text-foreground"
      >
        {formatValue(component.value)}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function CompensationBreakdown({ offer }: CompensationBreakdownProps) {
  const locale = useLocale();
  const fmtValue = (amount: number) => formatLPA(amount, locale);

  const components: CompensationComponent[] = [
    offer.baseSalary,
    offer.variable,
    offer.equity,
    offer.benefits,
    offer.signingBonus,
  ];

  return (
    <div data-testid="compensation-breakdown" className="space-y-3">
      <h3 className="text-base font-semibold text-foreground">
        Compensation Breakdown
      </h3>

      <div className="space-y-2">
        {components.map((comp) => (
          <CompensationRow key={comp.name} component={comp} formatValue={fmtValue} />
        ))}
      </div>

      {/* Total compensation */}
      <div
        data-testid="total-compensation"
        className="flex items-center justify-between rounded-md border-2 border-primary bg-primary/5 px-4 py-3"
      >
        <span className="text-sm font-semibold text-foreground">
          Total Compensation
        </span>
        <span className="text-base font-bold tabular-nums text-primary">
          {fmtValue(offer.totalCompensation)}
        </span>
      </div>
    </div>
  );
}
