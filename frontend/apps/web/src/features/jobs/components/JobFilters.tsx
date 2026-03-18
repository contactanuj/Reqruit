"use client";

// JobFilters.tsx — Filter and search for saved jobs (FE-5.4)
// Client-side filtering with URL param persistence.

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { JobFilters as JobFiltersType, JobStatus, RemotePreference, SavedJob } from "../types";

export interface JobFiltersProps {
  onFiltersChange: (filters: JobFiltersType) => void;
}

const REMOTE_OPTIONS: RemotePreference[] = ["Remote", "Hybrid", "On-site"];
const STATUS_OPTIONS: { value: JobStatus; label: string }[] = [
  { value: "saved", label: "Saved" },
  { value: "applied", label: "Applied" },
  { value: "phone_screen", label: "Phone Screen" },
  { value: "interview", label: "Interview" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
  { value: "withdrawn", label: "Withdrawn" },
];

export function JobFilters({ onFiltersChange }: JobFiltersProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Initialize from URL params
  const [query, setQuery] = useState(searchParams.get("q") ?? "");
  const [statuses, setStatuses] = useState<JobStatus[]>(
    (searchParams.get("status")?.split(",").filter(Boolean) ?? []) as JobStatus[]
  );
  const [remotes, setRemotes] = useState<RemotePreference[]>(
    (searchParams.get("remote")?.split(",").filter(Boolean) ?? []) as RemotePreference[]
  );
  const [salaryMin, setSalaryMin] = useState(searchParams.get("salary_min") ?? "");
  const [salaryMax, setSalaryMax] = useState(searchParams.get("salary_max") ?? "");
  const [dateFrom, setDateFrom] = useState(searchParams.get("date_from") ?? "");
  const [dateTo, setDateTo] = useState(searchParams.get("date_to") ?? "");

  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Build filters object and sync to URL
  const syncFilters = useCallback(
    (
      q: string,
      sts: JobStatus[],
      rem: RemotePreference[],
      sMin: string,
      sMax: string,
      dFrom: string,
      dTo: string
    ) => {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (sts.length) params.set("status", sts.join(","));
      if (rem.length) params.set("remote", rem.join(","));
      if (sMin) params.set("salary_min", sMin);
      if (sMax) params.set("salary_max", sMax);
      if (dFrom) params.set("date_from", dFrom);
      if (dTo) params.set("date_to", dTo);

      router.replace(`?${params.toString()}`, { scroll: false });

      onFiltersChange({
        q: q || undefined,
        status: sts.length ? sts : undefined,
        remote: rem.length ? rem : undefined,
        salary_min: sMin ? Number(sMin) : undefined,
        salary_max: sMax ? Number(sMax) : undefined,
        date_from: dFrom || undefined,
        date_to: dTo || undefined,
      });
    },
    [router, onFiltersChange]
  );

  // Debounced search
  function handleQueryChange(val: string) {
    setQuery(val);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      syncFilters(val, statuses, remotes, salaryMin, salaryMax, dateFrom, dateTo);
    }, 200);
  }

  function toggleStatus(status: JobStatus) {
    const next = statuses.includes(status)
      ? statuses.filter((s) => s !== status)
      : [...statuses, status];
    setStatuses(next);
    syncFilters(query, next, remotes, salaryMin, salaryMax, dateFrom, dateTo);
  }

  function toggleRemote(remote: RemotePreference) {
    const next = remotes.includes(remote)
      ? remotes.filter((r) => r !== remote)
      : [...remotes, remote];
    setRemotes(next);
    syncFilters(query, statuses, next, salaryMin, salaryMax, dateFrom, dateTo);
  }

  const salaryDebounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clean up debounce timers on unmount
  useEffect(() => {
    const queryTimer = debounceTimer;
    const salaryTimer = salaryDebounceTimer;
    return () => {
      if (queryTimer.current) clearTimeout(queryTimer.current);
      if (salaryTimer.current) clearTimeout(salaryTimer.current);
    };
  }, []);

  function handleSalaryMin(val: string) {
    setSalaryMin(val);
    if (salaryDebounceTimer.current) clearTimeout(salaryDebounceTimer.current);
    salaryDebounceTimer.current = setTimeout(() => {
      syncFilters(query, statuses, remotes, val, salaryMax, dateFrom, dateTo);
    }, 200);
  }

  function handleSalaryMax(val: string) {
    setSalaryMax(val);
    if (salaryDebounceTimer.current) clearTimeout(salaryDebounceTimer.current);
    salaryDebounceTimer.current = setTimeout(() => {
      syncFilters(query, statuses, remotes, salaryMin, val, dateFrom, dateTo);
    }, 200);
  }

  function clearAll() {
    setQuery("");
    setStatuses([]);
    setRemotes([]);
    setSalaryMin("");
    setSalaryMax("");
    setDateFrom("");
    setDateTo("");
    router.replace("?", { scroll: false });
    onFiltersChange({});
  }

  const hasActiveFilters =
    !!query ||
    statuses.length > 0 ||
    remotes.length > 0 ||
    !!salaryMin ||
    !!salaryMax ||
    !!dateFrom ||
    !!dateTo;

  // Active filter chips
  const chips: { label: string; onRemove: () => void }[] = [];
  if (query) chips.push({ label: `Search: "${query}"`, onRemove: () => handleQueryChange("") });
  statuses.forEach((s) =>
    chips.push({
      label: STATUS_OPTIONS.find((o) => o.value === s)?.label ?? s,
      onRemove: () => toggleStatus(s),
    })
  );
  remotes.forEach((r) =>
    chips.push({ label: r, onRemove: () => toggleRemote(r) })
  );
  if (salaryMin) chips.push({ label: `Min salary: ${salaryMin}`, onRemove: () => handleSalaryMin("") });
  if (salaryMax) chips.push({ label: `Max salary: ${salaryMax}`, onRemove: () => handleSalaryMax("") });

  return (
    <div className="flex flex-col gap-3" data-testid="job-filters">
      {/* Search input */}
      <div className="flex items-center gap-2">
        <input
          type="search"
          aria-label="Search jobs"
          placeholder="Search by company, role, or location…"
          value={query}
          onChange={(e) => handleQueryChange(e.target.value)}
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {hasActiveFilters && (
          <button
            type="button"
            onClick={clearAll}
            className="text-xs text-muted-foreground underline hover:no-underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Active filter chips */}
      {chips.length > 0 && (
        <div className="flex flex-wrap gap-2" aria-label="Active filters">
          {chips.map((chip) => (
            <span
              key={chip.label}
              className="inline-flex items-center gap-1 rounded-full border border-border bg-muted px-2.5 py-0.5 text-xs"
            >
              {chip.label}
              <button
                type="button"
                aria-label={`Remove filter: ${chip.label}`}
                onClick={chip.onRemove}
                className="ml-1 text-muted-foreground hover:text-foreground"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Filter panel */}
      <div className="flex flex-wrap gap-4 text-sm">
        {/* Remote preference */}
        <fieldset>
          <legend className="text-xs font-semibold text-muted-foreground mb-1">Remote</legend>
          <div className="flex flex-wrap gap-2">
            {REMOTE_OPTIONS.map((opt) => (
              <label key={opt} className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={remotes.includes(opt)}
                  onChange={() => toggleRemote(opt)}
                  className="rounded border-border"
                />
                <span>{opt}</span>
              </label>
            ))}
          </div>
        </fieldset>

        {/* Status */}
        <fieldset>
          <legend className="text-xs font-semibold text-muted-foreground mb-1">Status</legend>
          <div className="flex flex-wrap gap-2">
            {STATUS_OPTIONS.map((opt) => (
              <label key={opt.value} className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={statuses.includes(opt.value)}
                  onChange={() => toggleStatus(opt.value)}
                  className="rounded border-border"
                />
                <span>{opt.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        {/* Salary range */}
        <fieldset>
          <legend className="text-xs font-semibold text-muted-foreground mb-1">Salary range</legend>
          <div className="flex items-center gap-2">
            <input
              type="number"
              aria-label="Minimum salary"
              placeholder="Min"
              value={salaryMin}
              onChange={(e) => handleSalaryMin(e.target.value)}
              className="w-24 rounded-md border border-border bg-background px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <span className="text-muted-foreground">–</span>
            <input
              type="number"
              aria-label="Maximum salary"
              placeholder="Max"
              value={salaryMax}
              onChange={(e) => handleSalaryMax(e.target.value)}
              className="w-24 rounded-md border border-border bg-background px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </fieldset>

        {/* Date range */}
        <fieldset>
          <legend className="text-xs font-semibold text-muted-foreground mb-1">Date range</legend>
          <div className="flex items-center gap-2">
            <input
              type="date"
              aria-label="Added after"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                syncFilters(query, statuses, remotes, salaryMin, salaryMax, e.target.value, dateTo);
              }}
              className="w-36 rounded-md border border-border bg-background px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <span className="text-muted-foreground">–</span>
            <input
              type="date"
              aria-label="Added before"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                syncFilters(query, statuses, remotes, salaryMin, salaryMax, dateFrom, e.target.value);
              }}
              className="w-36 rounded-md border border-border bg-background px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </fieldset>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Client-side filter utility
// ---------------------------------------------------------------------------

export function applyJobFilters(jobs: SavedJob[], filters: JobFiltersType): SavedJob[] {
  let result = jobs;

  if (filters.q) {
    const q = filters.q.toLowerCase();
    result = result.filter(
      (j) =>
        j.company.toLowerCase().includes(q) ||
        j.title.toLowerCase().includes(q) ||
        (j.location ?? "").toLowerCase().includes(q)
    );
  }

  if (filters.status?.length) {
    result = result.filter((j) => filters.status!.includes(j.status));
  }

  if (filters.remote?.length) {
    result = result.filter(
      (j) => j.remote_preference && filters.remote!.includes(j.remote_preference)
    );
  }

  if (filters.salary_min != null) {
    result = result.filter((j) => (j.salary_min ?? 0) >= filters.salary_min!);
  }

  if (filters.salary_max != null) {
    result = result.filter((j) => (j.salary_max ?? filters.salary_max!) <= filters.salary_max!);
  }

  if (filters.date_from) {
    const from = new Date(filters.date_from).getTime();
    result = result.filter((j) => new Date(j.created_at).getTime() >= from);
  }

  if (filters.date_to) {
    const to = new Date(filters.date_to).getTime();
    result = result.filter((j) => new Date(j.created_at).getTime() <= to);
  }

  return result;
}
