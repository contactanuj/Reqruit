// JobFilters.test.tsx — FE-5.4 tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { JobFilters, applyJobFilters } from "./JobFilters";
import type { SavedJob } from "../types";

// Mock next/navigation
const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  useSearchParams: () => ({
    get: (_key: string) => null,
    toString: () => "",
  }),
}));

beforeEach(() => {
  mockReplace.mockClear();
  vi.clearAllMocks();
});

describe("JobFilters (FE-5.4)", () => {
  it("renders search input and filter checkboxes", () => {
    render(<JobFilters onFiltersChange={vi.fn()} />);
    expect(screen.getByRole("searchbox", { name: /search jobs/i })).toBeInTheDocument();
    // "Remote" appears as legend and as checkbox label — use getAllByText
    expect(screen.getAllByText("Remote").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Hybrid")).toBeInTheDocument();
  });

  it("debounces search input — calls onFiltersChange after 200ms", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const onFiltersChange = vi.fn();
    const user = userEvent.setup({ delay: null });
    render(<JobFilters onFiltersChange={onFiltersChange} />);

    await user.type(screen.getByRole("searchbox"), "React");

    // Not called immediately (debounce pending)
    // Advance time past the 200ms debounce
    act(() => vi.advanceTimersByTime(300));

    expect(onFiltersChange).toHaveBeenCalled();
    const call = onFiltersChange.mock.calls[onFiltersChange.mock.calls.length - 1][0];
    expect(call.q).toBe("React");
    vi.useRealTimers();
  });

  it("shows filter chips for active status filter", async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    render(<JobFilters onFiltersChange={onFiltersChange} />);

    // Click "Saved" checkbox in status section
    const savedCheckboxes = screen.getAllByRole("checkbox");
    // Saved is the 4th checkbox (after 3 remote checkboxes)
    await user.click(savedCheckboxes[3]);

    // After click, onFiltersChange should be called with status filter
    expect(onFiltersChange).toHaveBeenCalled();
    const lastCall = onFiltersChange.mock.calls[onFiltersChange.mock.calls.length - 1][0];
    expect(lastCall.status).toContain("saved");
  });

  it("clears all filters when Clear filters is clicked", async () => {
    const user = userEvent.setup();
    const onFiltersChange = vi.fn();
    render(<JobFilters onFiltersChange={onFiltersChange} />);

    // Apply a filter first - click "Remote" checkbox option
    await user.click(screen.getAllByRole("checkbox")[0]);

    // Clear all button should now appear since there's an active filter
    await user.click(screen.getByText(/Clear filters/i));

    // The last call should have empty filters
    const lastCall = onFiltersChange.mock.calls[onFiltersChange.mock.calls.length - 1][0];
    expect(lastCall).toEqual({});
  });
});

describe("applyJobFilters", () => {
  const jobs: SavedJob[] = [
    {
      id: "1",
      title: "React Developer",
      company: "Acme",
      location: "Remote",
      status: "saved",
      remote_preference: "Remote",
      salary_min: 1_000_000,
      salary_max: 1_500_000,
      created_at: "2026-01-15T00:00:00Z",
    },
    {
      id: "2",
      title: "Python Engineer",
      company: "Beta Inc",
      location: "London",
      status: "applied",
      remote_preference: "On-site",
      salary_min: 2_000_000,
      salary_max: 2_500_000,
      created_at: "2026-02-20T00:00:00Z",
    },
  ];

  it("filters by search query (company, role, location)", () => {
    expect(applyJobFilters(jobs, { q: "react" })).toHaveLength(1);
    expect(applyJobFilters(jobs, { q: "london" })).toHaveLength(1);
    expect(applyJobFilters(jobs, { q: "beta" })).toHaveLength(1);
    expect(applyJobFilters(jobs, { q: "zzz" })).toHaveLength(0);
  });

  it("filters by status", () => {
    expect(applyJobFilters(jobs, { status: ["saved"] })).toHaveLength(1);
    expect(applyJobFilters(jobs, { status: ["applied"] })).toHaveLength(1);
    expect(applyJobFilters(jobs, { status: ["saved", "applied"] })).toHaveLength(2);
  });

  it("filters by remote preference", () => {
    expect(applyJobFilters(jobs, { remote: ["Remote"] })).toHaveLength(1);
    expect(applyJobFilters(jobs, { remote: ["On-site"] })).toHaveLength(1);
  });

  it("returns empty state message when no jobs match", () => {
    const result = applyJobFilters(jobs, { q: "nonexistent" });
    expect(result).toHaveLength(0);
  });
});
