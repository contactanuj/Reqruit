// JobsKanbanView.test.tsx — FE-5.3 tests

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { JobsKanbanView } from "./JobsKanbanView";
import type { SavedJob } from "../types";

const mockJobs: SavedJob[] = [
  {
    id: "job-1",
    title: "Frontend Developer",
    company: "Acme Corp",
    location: "Remote",
    status: "saved",
    created_at: "2026-03-01T00:00:00Z",
  },
  {
    id: "job-2",
    title: "Backend Developer",
    company: "Corp B",
    location: "New York",
    status: "applied",
    created_at: "2026-03-02T00:00:00Z",
  },
  {
    id: "job-3",
    title: "DevOps Engineer",
    company: "StartupX",
    location: "San Francisco",
    status: "saved",
    created_at: "2026-03-03T00:00:00Z",
  },
];

describe("JobsKanbanView (FE-5.3)", () => {
  it("renders all kanban columns", () => {
    render(<JobsKanbanView jobs={mockJobs} locale="US" />);

    expect(screen.getByText("Saved")).toBeInTheDocument();
    expect(screen.getByText("Applied")).toBeInTheDocument();
    expect(screen.getByText("Phone Screen")).toBeInTheDocument();
    expect(screen.getByText("Interview")).toBeInTheDocument();
    expect(screen.getByText("Offer")).toBeInTheDocument();
    expect(screen.getByText("Rejected")).toBeInTheDocument();
    expect(screen.getByText("Withdrawn")).toBeInTheDocument();
  });

  it("groups jobs by status into correct columns", () => {
    render(<JobsKanbanView jobs={mockJobs} locale="US" />);

    expect(screen.getByText("Frontend Developer")).toBeInTheDocument();
    expect(screen.getByText("Backend Developer")).toBeInTheDocument();
    expect(screen.getByText("DevOps Engineer")).toBeInTheDocument();

    // Saved column should show count of 2
    const savedColumn = screen.getByLabelText("Saved column");
    expect(savedColumn).toHaveTextContent("2");

    // Applied column should show count of 1
    const appliedColumn = screen.getByLabelText("Applied column");
    expect(appliedColumn).toHaveTextContent("1");
  });

  it("shows 'No jobs' for empty columns", () => {
    render(<JobsKanbanView jobs={[]} locale="US" />);

    const noJobsLabels = screen.getAllByText("No jobs");
    // All 7 columns should show "No jobs"
    expect(noJobsLabels).toHaveLength(7);
  });

  it("renders skeleton cards when isPending is true", () => {
    render(<JobsKanbanView jobs={[]} isPending locale="US" />);

    expect(screen.getByLabelText("Loading kanban board")).toBeInTheDocument();
  });

  it("renders the kanban board with data-testid", () => {
    render(<JobsKanbanView jobs={mockJobs} locale="US" />);

    expect(screen.getByTestId("kanban-board")).toBeInTheDocument();
  });
});
