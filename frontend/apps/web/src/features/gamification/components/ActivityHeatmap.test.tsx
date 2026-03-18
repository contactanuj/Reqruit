import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ActivityHeatmap } from "./ActivityHeatmap";
import { XPTrendChart } from "./XPTrendChart";
import type { ActivityDay } from "../hooks/useGamification";

// Generate 365 days of sample activity
function makeActivityDays(days: number): ActivityDay[] {
  const result: ActivityDay[] = [];
  const today = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    result.push({
      date: d.toISOString().substring(0, 10),
      count: i % 3, // 0, 1, 2 cycle
      xpEarned: i % 3 === 0 ? 0 : (i % 3) * 50,
    });
  }
  return result;
}

describe("ActivityHeatmap", () => {
  it("renders heatmap container with correct aria-label", () => {
    const days = makeActivityDays(365);
    render(<ActivityHeatmap days={days} />);

    const heatmap = screen.getByRole("img", {
      name: "Activity heatmap for the past 52 weeks",
    });
    expect(heatmap).toBeInTheDocument();
  });

  it("renders 52×7 = 364 cells", () => {
    const days = makeActivityDays(365);
    const { container } = render(<ActivityHeatmap days={days} />);

    // Each cell is a <rect> with an aria-label containing "activities"
    const cells = container.querySelectorAll("rect[aria-label]");
    expect(cells).toHaveLength(52 * 7);
  });

  it("shows tooltip with locale-formatted date for IN locale", () => {
    const days = [
      {
        date: "2026-01-15",
        count: 3,
        xpEarned: 150,
      },
    ];
    render(<ActivityHeatmap days={days} locale="en-IN" />);

    // IN locale → DD/MM/YYYY format
    const cell = screen.getByLabelText(/15\/01\/2026.*3 activities/);
    expect(cell).toBeInTheDocument();
  });

  it("provides sr-only summary with most active day", () => {
    const days = makeActivityDays(30);
    render(<ActivityHeatmap days={days} />);

    // Check that sr-only text exists
    const srText = screen.getByText(/Most active:/);
    expect(srText).toBeInTheDocument();
  });
});

describe("XPTrendChart", () => {
  it("renders chart container with aria-label", () => {
    const days = makeActivityDays(30);
    render(<XPTrendChart days={days} />);

    const chart = screen.getByRole("img", {
      name: "XP trend chart for the past 30 days",
    });
    expect(chart).toBeInTheDocument();
  });

  it("renders with empty data without crashing", () => {
    render(<XPTrendChart days={[]} />);
    expect(
      screen.getByRole("img", { name: "XP trend chart for the past 30 days" })
    ).toBeInTheDocument();
  });
});
