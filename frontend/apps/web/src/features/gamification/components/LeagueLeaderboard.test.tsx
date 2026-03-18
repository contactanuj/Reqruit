// LeagueLeaderboard.test.tsx — FE-14.1 co-located tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { LeagueLeaderboard } from "./LeagueLeaderboard";
import type { LeaderboardData, LeaderboardEntry } from "../types";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("../hooks/useLeaderboard", async (importOriginal) => {
  const original = await importOriginal<typeof import("../hooks/useLeaderboard")>();
  return { ...original, useLeaderboardQuery: vi.fn() };
});

import { useLeaderboardQuery } from "../hooks/useLeaderboard";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeEntry(overrides: Partial<LeaderboardEntry> = {}): LeaderboardEntry {
  return {
    userId: "user-1",
    username: "alice",
    weeklyXp: 500,
    rank: 1,
    isCurrentUser: false,
    ...overrides,
  };
}

function makeLeaderboardData(
  overrides: Partial<LeaderboardData> = {},
): LeaderboardData {
  return {
    entries: [
      makeEntry({ userId: "user-1", username: "alice", rank: 1, weeklyXp: 500 }),
      makeEntry({ userId: "user-2", username: "bob", rank: 2, weeklyXp: 400 }),
      makeEntry({
        userId: "user-3",
        username: "charlie",
        rank: 3,
        weeklyXp: 300,
        isCurrentUser: true,
      }),
    ],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("LeagueLeaderboard (FE-14.1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state", () => {
    vi.mocked(useLeaderboardQuery).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as ReturnType<typeof useLeaderboardQuery>);

    render(<LeagueLeaderboard />);

    expect(screen.getByTestId("loading-state")).toBeInTheDocument();
    expect(screen.getByText("Loading leaderboard…")).toBeInTheDocument();
  });

  it("renders empty state when no entries", () => {
    vi.mocked(useLeaderboardQuery).mockReturnValue({
      data: { entries: [] },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useLeaderboardQuery>);

    render(<LeagueLeaderboard />);

    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
  });

  it("renders leaderboard entries with accessible table headers", () => {
    vi.mocked(useLeaderboardQuery).mockReturnValue({
      data: makeLeaderboardData(),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useLeaderboardQuery>);

    render(<LeagueLeaderboard />);

    expect(screen.getByTestId("leaderboard")).toBeInTheDocument();

    // Accessible table headers
    const headers = screen.getAllByRole("columnheader");
    expect(headers).toHaveLength(3);
    expect(headers[0]).toHaveTextContent("Rank");
    expect(headers[1]).toHaveTextContent("Player");
    expect(headers[2]).toHaveTextContent("Weekly XP");
  });

  it("renders rows for each entry", () => {
    vi.mocked(useLeaderboardQuery).mockReturnValue({
      data: makeLeaderboardData(),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useLeaderboardQuery>);

    render(<LeagueLeaderboard />);

    expect(screen.getByTestId("leaderboard-row-user-1")).toBeInTheDocument();
    expect(screen.getByTestId("leaderboard-row-user-2")).toBeInTheDocument();
  });

  it("highlights current user with 'You' badge", () => {
    vi.mocked(useLeaderboardQuery).mockReturnValue({
      data: makeLeaderboardData(),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useLeaderboardQuery>);

    render(<LeagueLeaderboard />);

    const currentUserRow = screen.getByTestId("current-user-row");
    expect(currentUserRow).toBeInTheDocument();
    expect(currentUserRow).toHaveTextContent("charlie");
    expect(currentUserRow).toHaveTextContent("You");
  });

  it("shows last week winner banner when available", () => {
    vi.mocked(useLeaderboardQuery).mockReturnValue({
      data: makeLeaderboardData({
        lastWeekWinner: { username: "diana", xp: 1200 },
      }),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useLeaderboardQuery>);

    render(<LeagueLeaderboard />);

    const banner = screen.getByTestId("last-week-winner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent("diana");
    expect(banner).toHaveTextContent("1,200 XP");
  });

  it("shows current user rank outside top 20", () => {
    // 20 entries, none is current user
    const entries: LeaderboardEntry[] = Array.from({ length: 20 }, (_, i) =>
      makeEntry({
        userId: `user-${i}`,
        username: `player-${i}`,
        rank: i + 1,
        weeklyXp: 1000 - i * 10,
        isCurrentUser: false,
      }),
    );

    vi.mocked(useLeaderboardQuery).mockReturnValue({
      data: {
        entries,
        currentUserEntry: makeEntry({
          userId: "user-me",
          username: "me",
          rank: 42,
          weeklyXp: 150,
          isCurrentUser: true,
        }),
      },
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useLeaderboardQuery>);

    render(<LeagueLeaderboard />);

    const outsideRank = screen.getByTestId("user-rank-outside");
    expect(outsideRank).toBeInTheDocument();
    expect(outsideRank).toHaveTextContent("#42");
    expect(outsideRank).toHaveTextContent("150 XP");
  });

  it("does not show outside-rank when user is in top 20", () => {
    vi.mocked(useLeaderboardQuery).mockReturnValue({
      data: makeLeaderboardData({
        currentUserEntry: makeEntry({
          userId: "user-3",
          username: "charlie",
          rank: 3,
          weeklyXp: 300,
          isCurrentUser: true,
        }),
      }),
      isLoading: false,
      isError: false,
    } as ReturnType<typeof useLeaderboardQuery>);

    render(<LeagueLeaderboard />);

    expect(screen.queryByTestId("user-rank-outside")).not.toBeInTheDocument();
  });

  it("renders error/empty state on fetch error", () => {
    vi.mocked(useLeaderboardQuery).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as ReturnType<typeof useLeaderboardQuery>);

    render(<LeagueLeaderboard />);

    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    expect(screen.getByText("Unable to load leaderboard data.")).toBeInTheDocument();
  });
});
