// SessionHistory.test.tsx — FE-11.5 co-located tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionHistory } from "./SessionHistory";
import type { SessionSummary } from "../types";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseSessionHistoryQuery = vi.fn();

vi.mock("../hooks/useSessionHistory", () => ({
  useSessionHistoryQuery: (...args: unknown[]) => mockUseSessionHistoryQuery(...args),
}));

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const MOCK_SESSIONS: SessionSummary[] = [
  {
    id: "sess-1",
    date: "2026-03-15",
    type: "behavioral",
    duration: 30,
    overallScore: 85,
  },
  {
    id: "sess-2",
    date: "2026-03-10",
    type: "technical",
    duration: 45,
    overallScore: 65,
  },
  {
    id: "sess-3",
    date: "2026-03-05",
    type: "system_design",
    duration: 60,
    overallScore: 42,
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SessionHistory (FE-11.5)", () => {
  // 1. Shows loading state
  it("shows loading state when data is loading", () => {
    mockUseSessionHistoryQuery.mockReturnValue({ data: undefined, isLoading: true });

    render(<SessionHistory onSelectSession={vi.fn()} />);

    expect(screen.getByTestId("loading-state")).toBeInTheDocument();
    expect(screen.getByTestId("loading-state")).toHaveTextContent("Loading sessions");
  });

  // 2. Renders session rows
  it("renders session rows with correct data", () => {
    mockUseSessionHistoryQuery.mockReturnValue({ data: MOCK_SESSIONS, isLoading: false });

    render(<SessionHistory onSelectSession={vi.fn()} />);

    expect(screen.getByTestId("session-row-sess-1")).toBeInTheDocument();
    expect(screen.getByTestId("session-row-sess-2")).toBeInTheDocument();
    expect(screen.getByTestId("session-row-sess-3")).toBeInTheDocument();

    // Check content of first row
    const row1 = screen.getByTestId("session-row-sess-1");
    expect(row1).toHaveTextContent("2026-03-15");
    expect(row1).toHaveTextContent("Behavioral");
    expect(row1).toHaveTextContent("30 min");
    expect(row1).toHaveTextContent("85");

    // Check type labels
    const row2 = screen.getByTestId("session-row-sess-2");
    expect(row2).toHaveTextContent("Technical");

    const row3 = screen.getByTestId("session-row-sess-3");
    expect(row3).toHaveTextContent("System Design");
  });

  // 3. Click row calls onSelectSession
  it("calls onSelectSession when a row is clicked", async () => {
    mockUseSessionHistoryQuery.mockReturnValue({ data: MOCK_SESSIONS, isLoading: false });
    const onSelect = vi.fn();
    const user = userEvent.setup();

    render(<SessionHistory onSelectSession={onSelect} />);

    await user.click(screen.getByTestId("session-row-sess-2"));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("sess-2");
  });

  // 4. Shows empty state
  it("shows empty state when no sessions exist", () => {
    mockUseSessionHistoryQuery.mockReturnValue({ data: [], isLoading: false });

    render(<SessionHistory onSelectSession={vi.fn()} />);

    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state")).toHaveTextContent("No sessions yet");
  });

  it("shows empty state when data is undefined", () => {
    mockUseSessionHistoryQuery.mockReturnValue({ data: undefined, isLoading: false });

    render(<SessionHistory onSelectSession={vi.fn()} />);

    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
  });

  // 5. Displays score with correct color coding
  it("displays scores with correct color coding", () => {
    mockUseSessionHistoryQuery.mockReturnValue({ data: MOCK_SESSIONS, isLoading: false });

    render(<SessionHistory onSelectSession={vi.fn()} />);

    // Score >= 80 → green
    const row1 = screen.getByTestId("session-row-sess-1");
    const score1 = row1.querySelector("td:last-child")!;
    expect(score1).toHaveTextContent("85");
    expect(score1.className).toContain("text-green-600");

    // Score >= 60 → amber
    const row2 = screen.getByTestId("session-row-sess-2");
    const score2 = row2.querySelector("td:last-child")!;
    expect(score2).toHaveTextContent("65");
    expect(score2.className).toContain("text-amber-600");

    // Score < 60 → red
    const row3 = screen.getByTestId("session-row-sess-3");
    const score3 = row3.querySelector("td:last-child")!;
    expect(score3).toHaveTextContent("42");
    expect(score3.className).toContain("text-red-600");
  });
});
