// MarketPositionChart.test.tsx — FE-12.2 co-located tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MarketPositionChart } from "./MarketPositionChart";
import type { MarketPosition } from "../types";

// ---------------------------------------------------------------------------
// Mocks — mock recharts components as simple divs
// ---------------------------------------------------------------------------

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("recharts", () => ({
  ComposedChart: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
    <div data-testid="mock-composed-chart" {...props}>{children}</div>
  ),
  Bar: (props: Record<string, unknown>) => <div data-testid="mock-bar" data-datakey={props.dataKey} />,
  XAxis: () => <div data-testid="mock-xaxis" />,
  YAxis: () => <div data-testid="mock-yaxis" />,
  CartesianGrid: () => <div data-testid="mock-cartesian-grid" />,
  Tooltip: () => <div data-testid="mock-tooltip" />,
  ReferenceLine: (props: Record<string, unknown>) => (
    <div data-testid="mock-reference-line" data-y={props.y} />
  ),
  ResponsiveContainer: ({ children }: React.PropsWithChildren) => (
    <div data-testid="mock-responsive-container">{children}</div>
  ),
  Cell: () => <div data-testid="mock-cell" />,
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockMarketPosition: MarketPosition = {
  p25: 120000,
  p50: 145000,
  p75: 170000,
  p90: 200000,
  userPercentile: 68,
  role: "Senior Software Engineer",
  city: "San Francisco",
};

const userTotal = 160000;

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("MarketPositionChart (FE-12.2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the chart container", () => {
    render(
      <MarketPositionChart
        marketPosition={mockMarketPosition}
        userTotal={userTotal}
      />,
    );

    expect(screen.getByTestId("market-position-chart")).toBeInTheDocument();
  });

  it("shows the percentile summary text", () => {
    render(
      <MarketPositionChart
        marketPosition={mockMarketPosition}
        userTotal={userTotal}
      />,
    );

    const summary = screen.getByTestId("percentile-summary");
    expect(summary).toHaveTextContent(
      "Your offer is at the 68th percentile for Senior Software Engineer in San Francisco",
    );
  });

  it("has an aria-label with percentile summary for accessibility", () => {
    render(
      <MarketPositionChart
        marketPosition={mockMarketPosition}
        userTotal={userTotal}
      />,
    );

    const chartRegion = screen.getByRole("img");
    expect(chartRegion).toHaveAttribute(
      "aria-label",
      "Your offer is at the 68th percentile for Senior Software Engineer in San Francisco",
    );
  });

  it("renders the mock recharts components", () => {
    render(
      <MarketPositionChart
        marketPosition={mockMarketPosition}
        userTotal={userTotal}
      />,
    );

    expect(screen.getByTestId("mock-responsive-container")).toBeInTheDocument();
    expect(screen.getByTestId("mock-composed-chart")).toBeInTheDocument();
    expect(screen.getByTestId("mock-bar")).toBeInTheDocument();
    expect(screen.getByTestId("mock-reference-line")).toBeInTheDocument();
  });

  it("passes the user total to the ReferenceLine", () => {
    render(
      <MarketPositionChart
        marketPosition={mockMarketPosition}
        userTotal={userTotal}
      />,
    );

    expect(screen.getByTestId("mock-reference-line")).toHaveAttribute(
      "data-y",
      String(userTotal),
    );
  });

  it("shows the percentile badge with correct value", () => {
    render(
      <MarketPositionChart
        marketPosition={mockMarketPosition}
        userTotal={userTotal}
      />,
    );

    const badge = screen.getByTestId("percentile-badge");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent("P68");
  });

  it("uses green color for percentile >= 75", () => {
    const highPercentile = { ...mockMarketPosition, userPercentile: 82 };
    const { container } = render(
      <MarketPositionChart
        marketPosition={highPercentile}
        userTotal={userTotal}
      />,
    );

    const badge = screen.getByTestId("percentile-badge");
    expect(badge).toHaveTextContent("P82");
    // The text should have green color class
    const percentileSpan = badge.querySelector(".text-green-600, .text-green-400");
    expect(percentileSpan).not.toBeNull();
  });

  it("uses red color for percentile < 50", () => {
    const lowPercentile = { ...mockMarketPosition, userPercentile: 30 };
    render(
      <MarketPositionChart
        marketPosition={lowPercentile}
        userTotal={userTotal}
      />,
    );

    const badge = screen.getByTestId("percentile-badge");
    expect(badge).toHaveTextContent("P30");
    const percentileSpan = badge.querySelector(".text-red-600, .text-red-400");
    expect(percentileSpan).not.toBeNull();
  });

  it("has a heading for Market Position", () => {
    render(
      <MarketPositionChart
        marketPosition={mockMarketPosition}
        userTotal={userTotal}
      />,
    );

    expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent(
      "Market Position",
    );
  });
});
