"use client";

// OfferComparison.tsx — FE-12.3: Side-by-side offer comparison table
// Uses @tanstack/react-table with sticky first column and "Best" badge on highest values.

import * as React from "react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import DOMPurify from "dompurify";
import { formatLPA } from "@repo/ui/lib/locale";
import { useLocale } from "@repo/ui/hooks";
import type { ParsedOffer } from "../types";

interface OfferComparisonProps {
  offers: ParsedOffer[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface ComparisonRow {
  label: string;
  values: { offerId: string; value: number; isBest: boolean }[];
}

function buildRows(offers: ParsedOffer[]): ComparisonRow[] {
  const fields = [
    { label: "Base Salary", key: "baseSalary" as const },
    { label: "Variable", key: "variable" as const },
    { label: "Equity", key: "equity" as const },
    { label: "Benefits", key: "benefits" as const },
    { label: "Signing Bonus", key: "signingBonus" as const },
    { label: "Total Compensation", key: null },
  ];

  return fields.map(({ label, key }) => {
    const values = offers.map((offer) => ({
      offerId: offer.id,
      value: key ? offer[key].value : offer.totalCompensation,
      isBest: false,
    }));

    // Mark the highest value as "best"
    const maxValue = Math.max(...values.map((v) => v.value));
    const distinctValues = new Set(values.map((v) => v.value));
    // Only mark best if values differ
    if (distinctValues.size > 1) {
      for (const v of values) {
        if (v.value === maxValue) {
          v.isBest = true;
        }
      }
    }

    return { label, values };
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function OfferComparison({ offers }: OfferComparisonProps) {
  const locale = useLocale();
  const [selectedIds, setSelectedIds] = React.useState<Set<string>>(
    () => new Set(offers.map((o) => o.id)),
  );

  const toggleOffer = (offerId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(offerId)) {
        next.delete(offerId);
      } else {
        next.add(offerId);
      }
      return next;
    });
  };

  const selectedOffers = offers.filter((o) => selectedIds.has(o.id));
  const rows = React.useMemo(() => buildRows(selectedOffers), [selectedOffers]);

  const columnHelper = createColumnHelper<ComparisonRow>();

  const columns = React.useMemo(
    () => [
      columnHelper.accessor("label", {
        header: "Component",
        cell: (info) => (
          <span className="font-medium text-foreground">
            {info.getValue()}
          </span>
        ),
      }),
      ...selectedOffers.map((offer, idx) =>
        columnHelper.display({
          id: `offer-${offer.id}`,
          header: () => (
            <span className="text-foreground">
              {DOMPurify.sanitize(`Offer ${idx + 1}`)}
            </span>
          ),
          cell: ({ row }) => {
            const val = row.original.values[idx];
            if (!val) return null;
            return (
              <span className="inline-flex items-center gap-2">
                <span className="tabular-nums">
                  {formatLPA(val.value, locale)}
                </span>
                {val.isBest && (
                  <span
                    data-testid={`best-badge-${row.original.label.toLowerCase().replace(/\s+/g, "-")}`}
                    className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800 dark:bg-green-900/30 dark:text-green-300"
                  >
                    Best
                  </span>
                )}
              </span>
            );
          },
        }),
      ),
    ],
    [selectedOffers, columnHelper, locale],
  );

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (offers.length < 2) {
    return (
      <p data-testid="comparison-minimum-notice" className="text-sm text-muted-foreground">
        Select at least 2 offers to compare.
      </p>
    );
  }

  return (
    <div data-testid="offer-comparison" className="space-y-4">
      {/* Offer selection checkboxes */}
      <fieldset data-testid="offer-selection">
        <legend className="mb-2 text-sm font-medium text-foreground">
          Select offers to compare
        </legend>
        <div className="flex flex-wrap gap-3">
          {offers.map((offer, idx) => (
            <label
              key={offer.id}
              className="inline-flex items-center gap-2 text-sm"
            >
              <input
                type="checkbox"
                checked={selectedIds.has(offer.id)}
                onChange={() => toggleOffer(offer.id)}
                data-testid={`offer-checkbox-${offer.id}`}
                className="h-4 w-4 rounded border-border accent-primary"
              />
              Offer {idx + 1}
            </label>
          ))}
        </div>
      </fieldset>

      {selectedOffers.length < 2 ? (
        <p className="text-sm text-muted-foreground">
          Select at least 2 offers to compare.
        </p>
      ) : (
      <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className="border-b border-border">
              {headerGroup.headers.map((header, idx) => (
                <th
                  key={header.id}
                  className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground ${
                    idx === 0 ? "sticky left-0 z-10 bg-background" : ""
                  }`}
                >
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className="border-b border-border last:border-b-0 hover:bg-muted/50"
            >
              {row.getVisibleCells().map((cell, idx) => (
                <td
                  key={cell.id}
                  className={`px-4 py-3 ${
                    idx === 0 ? "sticky left-0 z-10 bg-background" : ""
                  }`}
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      </div>
      )}
    </div>
  );
}
