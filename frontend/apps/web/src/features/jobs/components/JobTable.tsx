"use client";

// JobTable.tsx — Sortable table view for saved jobs (FE-5.3)
// Uses @tanstack/react-table v8

import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { formatDate, formatLPA, formatCTC } from "@repo/ui/lib/locale";
import type { LocaleCode } from "@repo/ui/lib/locale";
import type { SavedJob } from "../types";

const columnHelper = createColumnHelper<SavedJob>();

interface JobTableProps {
  jobs: SavedJob[];
  locale?: LocaleCode;
  onJobClick?: (job: SavedJob) => void;
}

const STATUS_LABEL: Record<string, string> = {
  saved: "Saved",
  applied: "Applied",
  phone_screen: "Phone Screen",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

export function JobTable({ jobs, locale = "US", onJobClick }: JobTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const columns = [
    columnHelper.accessor("company", {
      header: "Company",
      cell: (info) => <span className="font-medium">{info.getValue()}</span>,
    }),
    columnHelper.accessor("title", {
      header: "Role",
    }),
    columnHelper.accessor("created_at", {
      header: "Date Added",
      cell: (info) => formatDate(info.getValue(), locale),
    }),
    columnHelper.accessor("fit_score", {
      header: "Fit Score",
      cell: (info) => {
        const v = info.getValue();
        return v != null ? `${v}%` : "—";
      },
    }),
    columnHelper.accessor("status", {
      header: "Status",
      cell: (info) => STATUS_LABEL[info.getValue()] ?? info.getValue(),
    }),
    columnHelper.accessor("salary_max", {
      header: "CTC",
      cell: (info) => {
        const v = info.getValue();
        if (v == null) return "—";
        return locale === "IN" ? formatLPA(v, "IN") : formatCTC(v, "US");
      },
    }),
  ];

  const table = useReactTable({
    data: jobs,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="overflow-x-auto rounded-lg border border-border" data-testid="job-table">
      <table className="w-full text-sm">
        <thead>
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id} className="border-b border-border bg-muted/30">
              {headerGroup.headers.map((header) => (
                <th
                  key={header.id}
                  className={[
                    "px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-muted-foreground",
                    header.column.getCanSort() ? "cursor-pointer select-none" : "",
                  ].join(" ")}
                  onClick={header.column.getToggleSortingHandler()}
                  aria-sort={
                    header.column.getIsSorted()
                      ? header.column.getIsSorted() === "asc"
                        ? "ascending"
                        : "descending"
                      : "none"
                  }
                >
                  <span className="flex items-center gap-1">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getIsSorted() === "asc" && " ↑"}
                    {header.column.getIsSorted() === "desc" && " ↓"}
                  </span>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              className="border-b border-border last:border-0 hover:bg-muted/20 cursor-pointer transition-colors"
              onClick={() => onJobClick?.(row.original)}
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-4 py-3">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
          {jobs.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-sm text-muted-foreground">
                No jobs found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
