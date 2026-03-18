import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { XPWidget } from "./XPWidget";
import type { GamificationStatus } from "../hooks/useGamification";

vi.mock("../hooks/useGamification", async (importOriginal) => {
  const original = await importOriginal<typeof import("../hooks/useGamification")>();
  return { ...original, useGamificationStatus: vi.fn() };
});

import { useGamificationStatus } from "../hooks/useGamification";

const mockStatus: GamificationStatus = {
  xp: 1250,
  streakDays: 7,
  leagueTier: "Silver",
  leagueRank: 42,
};

describe("XPWidget", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders XP, streak, and league", () => {
    vi.mocked(useGamificationStatus).mockReturnValue({
      data: mockStatus,
    } as ReturnType<typeof useGamificationStatus>);

    render(<XPWidget />);

    // XP counter
    expect(screen.getByLabelText("XP: 1250 points")).toBeInTheDocument();
    // Streak
    expect(screen.getByLabelText("Streak: 7 days")).toBeInTheDocument();
    // League
    expect(screen.getByLabelText("League: Silver")).toBeInTheDocument();
  });

  it("has aria-live polite on XP counter", () => {
    vi.mocked(useGamificationStatus).mockReturnValue({
      data: mockStatus,
    } as ReturnType<typeof useGamificationStatus>);

    render(<XPWidget />);

    const xpEl = screen.getByLabelText("XP: 1250 points");
    expect(xpEl).toHaveAttribute("aria-live", "polite");
  });

  it("renders nothing when no data", () => {
    vi.mocked(useGamificationStatus).mockReturnValue({
      data: undefined,
    } as ReturnType<typeof useGamificationStatus>);

    const { container } = render(<XPWidget />);
    expect(container.firstChild).toBeNull();
  });

  it("renders compact mode for collapsed sidebar", () => {
    vi.mocked(useGamificationStatus).mockReturnValue({
      data: mockStatus,
    } as ReturnType<typeof useGamificationStatus>);

    render(<XPWidget compact />);

    expect(screen.getByTestId("xp-widget-compact")).toBeInTheDocument();
  });

  it("displays Gold league tier with correct label", () => {
    vi.mocked(useGamificationStatus).mockReturnValue({
      data: { ...mockStatus, leagueTier: "Gold" },
    } as ReturnType<typeof useGamificationStatus>);

    render(<XPWidget />);

    expect(screen.getByLabelText("League: Gold")).toBeInTheDocument();
  });
});
