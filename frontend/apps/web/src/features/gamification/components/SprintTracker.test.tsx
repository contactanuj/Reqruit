// SprintTracker.test.tsx — FE-14.2 co-located tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { SprintTracker } from "./SprintTracker";
import type { Sprint } from "../types";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockMutate = vi.fn();

vi.mock("../hooks/useSprints", async (importOriginal) => {
  const original = await importOriginal<typeof import("../hooks/useSprints")>();
  return {
    ...original,
    useSprintsQuery: vi.fn(),
    useGenerateRetrospective: vi.fn(() => ({
      mutate: mockMutate,
      isPending: false,
    })),
  };
});

import { useSprintsQuery, useGenerateRetrospective } from "../hooks/useSprints";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const activeSprint: Sprint = {
  id: "sprint-1",
  startDate: "2026-03-10",
  endDate: "2026-03-17",
  status: "active",
  goals: [
    {
      id: "goal-1",
      description: "Apply to 5 jobs",
      targetCount: 5,
      currentCount: 3,
    },
    {
      id: "goal-2",
      description: "Complete 3 interviews",
      targetCount: 3,
      currentCount: 1,
    },
  ],
};

const completedSprintWithRetro: Sprint = {
  id: "sprint-2",
  startDate: "2026-03-01",
  endDate: "2026-03-07",
  status: "completed",
  goals: [
    {
      id: "goal-3",
      description: "Send outreach",
      targetCount: 10,
      currentCount: 10,
    },
  ],
  retrospective: "<p>Great sprint! You completed all goals.</p>",
};

const completedSprintNoRetro: Sprint = {
  id: "sprint-3",
  startDate: "2026-03-01",
  endDate: "2026-03-07",
  status: "completed",
  goals: [
    {
      id: "goal-4",
      description: "Network",
      targetCount: 5,
      currentCount: 4,
    },
  ],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SprintTracker (FE-14.2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useGenerateRetrospective).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    } as unknown as ReturnType<typeof useGenerateRetrospective>);
  });

  it("renders loading state", () => {
    vi.mocked(useSprintsQuery).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useSprintsQuery>);

    render(<SprintTracker />);

    expect(screen.getByTestId("loading-state")).toBeInTheDocument();
    expect(screen.getByText("Loading sprint data…")).toBeInTheDocument();
  });

  it("renders no-sprint state when no sprints exist", () => {
    vi.mocked(useSprintsQuery).mockReturnValue({
      data: [],
      isLoading: false,
    } as ReturnType<typeof useSprintsQuery>);

    render(<SprintTracker />);

    expect(screen.getByTestId("no-sprint-state")).toBeInTheDocument();
  });

  it("renders active sprint with progress bars", () => {
    vi.mocked(useSprintsQuery).mockReturnValue({
      data: [activeSprint],
      isLoading: false,
    } as ReturnType<typeof useSprintsQuery>);

    render(<SprintTracker />);

    expect(screen.getByTestId("sprint-tracker")).toBeInTheDocument();
    expect(screen.getByTestId("sprint-goal-goal-1")).toBeInTheDocument();
    expect(screen.getByTestId("sprint-goal-goal-2")).toBeInTheDocument();

    // Progress bars
    const progressBar1 = screen.getByTestId("goal-progress-goal-1");
    expect(progressBar1).toHaveAttribute("role", "progressbar");
    expect(progressBar1).toHaveAttribute("aria-valuenow", "3");
    expect(progressBar1).toHaveAttribute("aria-valuemax", "5");

    const progressBar2 = screen.getByTestId("goal-progress-goal-2");
    expect(progressBar2).toHaveAttribute("aria-valuenow", "1");
    expect(progressBar2).toHaveAttribute("aria-valuemax", "3");
  });

  it("renders progress percentages correctly", () => {
    vi.mocked(useSprintsQuery).mockReturnValue({
      data: [activeSprint],
      isLoading: false,
    } as ReturnType<typeof useSprintsQuery>);

    render(<SprintTracker />);

    // 3/5 = 60%
    expect(screen.getByText("3/5 (60%)")).toBeInTheDocument();
    // 1/3 = 33%
    expect(screen.getByText("1/3 (33%)")).toBeInTheDocument();
  });

  it("renders retrospective card when available", () => {
    vi.mocked(useSprintsQuery).mockReturnValue({
      data: [completedSprintWithRetro],
      isLoading: false,
    } as ReturnType<typeof useSprintsQuery>);

    render(<SprintTracker />);

    expect(screen.getByTestId("retrospective-card")).toBeInTheDocument();
    expect(screen.getByText("AI Retrospective")).toBeInTheDocument();
    expect(
      screen.getByText("Great sprint! You completed all goals."),
    ).toBeInTheDocument();
  });

  it("auto-triggers retrospective generation for completed sprint without one", () => {
    vi.mocked(useSprintsQuery).mockReturnValue({
      data: [completedSprintNoRetro],
      isLoading: false,
    } as ReturnType<typeof useSprintsQuery>);

    render(<SprintTracker />);

    expect(mockMutate).toHaveBeenCalledOnce();
  });

  it("does NOT auto-trigger retrospective for sprint that has one", () => {
    vi.mocked(useSprintsQuery).mockReturnValue({
      data: [completedSprintWithRetro],
      isLoading: false,
    } as ReturnType<typeof useSprintsQuery>);

    render(<SprintTracker />);

    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("shows loading indicator when generating retrospective", () => {
    vi.mocked(useGenerateRetrospective).mockReturnValue({
      mutate: mockMutate,
      isPending: true,
    } as unknown as ReturnType<typeof useGenerateRetrospective>);

    vi.mocked(useSprintsQuery).mockReturnValue({
      data: [completedSprintNoRetro],
      isLoading: false,
    } as ReturnType<typeof useSprintsQuery>);

    render(<SprintTracker />);

    expect(screen.getByText("Generating retrospective…")).toBeInTheDocument();
  });

  it("prefers active sprint over completed sprint", () => {
    vi.mocked(useSprintsQuery).mockReturnValue({
      data: [completedSprintWithRetro, activeSprint],
      isLoading: false,
    } as ReturnType<typeof useSprintsQuery>);

    render(<SprintTracker />);

    // Should show the active sprint's goals
    expect(screen.getByTestId("sprint-goal-goal-1")).toBeInTheDocument();
    expect(screen.getByText("Active Sprint")).toBeInTheDocument();
  });
});
