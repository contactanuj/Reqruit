// JobCard.test.tsx — FE-5.1 tests

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { JobCard } from "./JobCard";
import type { SavedJob } from "../types";

const baseJob: SavedJob = {
  id: "job-1",
  title: "Senior Software Engineer",
  company: "Acme Corp",
  location: "Remote",
  fit_score: 87,
  roi_prediction: "High ROI",
  staleness_score: 5,
  posted_at: "2026-03-01T00:00:00Z",
  last_verified_at: "2026-03-10T00:00:00Z",
  created_at: "2026-03-01T00:00:00Z",
  status: "saved",
};

describe("JobCard (FE-5.1)", () => {
  it("renders company, role, location, fit score, and ROI", () => {
    render(<JobCard job={baseJob} locale="US" />);

    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    expect(screen.getByText("Senior Software Engineer")).toBeInTheDocument();
    expect(screen.getByText("Remote")).toBeInTheDocument();
    expect(screen.getByText("87% fit")).toBeInTheDocument();
    expect(screen.getByText("High ROI")).toBeInTheDocument();
  });

  it("renders freshness indicator with status label", () => {
    render(<JobCard job={baseJob} locale="US" />);
    // staleness_score = 5 → Fresh
    expect(screen.getByText("Fresh")).toBeInTheDocument();
  });

  it("shows LPA format for IN locale job with salary", () => {
    const inJob: SavedJob = {
      ...baseJob,
      salary_min: 2_000_000, // ₹20L
      salary_max: 2_500_000, // ₹25L
      locale: "IN",
    };
    render(<JobCard job={inJob} locale="IN" />);
    // Should show LPA format — ₹20L–₹25L
    expect(screen.getByText(/₹20L/)).toBeInTheDocument();
  });

  it("shows USD format for US locale job with salary", () => {
    const usJob: SavedJob = {
      ...baseJob,
      salary_min: 150_000,
      salary_max: 200_000,
    };
    render(<JobCard job={usJob} locale="US" />);
    // Should show $150K/$200K format
    expect(screen.getByText(/\$150K/)).toBeInTheDocument();
  });

  it("calls onClick when card is clicked", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<JobCard job={baseJob} locale="US" onClick={onClick} />);

    await user.click(screen.getByTestId("job-card"));
    expect(onClick).toHaveBeenCalledWith(baseJob);
  });

  it("shows Updated badge when isNew is true", () => {
    render(<JobCard job={baseJob} locale="US" isNew />);
    expect(screen.getByText("Updated")).toBeInTheDocument();
  });
});
