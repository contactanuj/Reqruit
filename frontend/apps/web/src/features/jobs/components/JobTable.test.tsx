// JobTable.test.tsx — FE-5.3 tests

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { JobTable } from "./JobTable";
import type { SavedJob } from "../types";

const jobs: SavedJob[] = [
  {
    id: "1",
    title: "React Developer",
    company: "Acme",
    location: "Remote",
    fit_score: 85,
    salary_max: 2_000_000,
    created_at: "2026-01-15T00:00:00Z",
    status: "saved",
  },
  {
    id: "2",
    title: "Node.js Developer",
    company: "Zeta",
    location: "London",
    fit_score: 70,
    salary_max: 1_500_000,
    created_at: "2026-02-20T00:00:00Z",
    status: "applied",
  },
  {
    id: "3",
    title: "Python Developer",
    company: "Beta",
    location: "Berlin",
    fit_score: 90,
    salary_max: 2_500_000,
    created_at: "2026-03-01T00:00:00Z",
    status: "interview",
  },
];

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

describe("JobTable (FE-5.3)", () => {
  it("renders all jobs in table", () => {
    render(<JobTable jobs={jobs} locale="US" />);

    expect(screen.getByText("React Developer")).toBeInTheDocument();
    expect(screen.getByText("Node.js Developer")).toBeInTheDocument();
    expect(screen.getByText("Python Developer")).toBeInTheDocument();
  });

  it("renders column headers for sortable columns", () => {
    render(<JobTable jobs={jobs} locale="US" />);

    expect(screen.getByText("Company")).toBeInTheDocument();
    expect(screen.getByText("Role")).toBeInTheDocument();
    expect(screen.getByText("Date Added")).toBeInTheDocument();
    expect(screen.getByText("Fit Score")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
  });

  it("sorts by company when clicking column header", async () => {
    const user = userEvent.setup();
    render(<JobTable jobs={jobs} locale="US" />);

    const companyHeader = screen.getByText("Company");
    await user.click(companyHeader);

    // After ascending sort: Acme, Beta, Zeta
    const rows = screen.getAllByRole("row");
    // Skip header row (index 0)
    const companies = rows.slice(1).map((row) => row.textContent ?? "");
    expect(companies[0]).toContain("Acme");
  });

  it("shows LPA format for IN locale", () => {
    render(<JobTable jobs={jobs} locale="IN" />);
    // ₹20L for 2_000_000
    expect(screen.getAllByText(/₹20L/).length).toBeGreaterThan(0);
  });

  it("calls onJobClick when a row is clicked", async () => {
    const user = userEvent.setup();
    const onJobClick = vi.fn();
    render(<JobTable jobs={jobs} locale="US" onJobClick={onJobClick} />);

    await user.click(screen.getByText("React Developer"));
    expect(onJobClick).toHaveBeenCalledWith(jobs[0]);
  });

  it("shows empty message when jobs array is empty", () => {
    render(<JobTable jobs={[]} locale="US" />);
    expect(screen.getByText("No jobs found")).toBeInTheDocument();
  });
});
