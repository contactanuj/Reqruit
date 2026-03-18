// BurnoutGauge.test.tsx — FE-13.2 co-located tests

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BurnoutGauge } from "./BurnoutGauge";

// Mock recharts to avoid SVG rendering issues in jsdom
vi.mock("recharts", () => ({
  RadialBarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="radial-bar-chart">{children}</div>
  ),
  RadialBar: () => <div data-testid="radial-bar" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

describe("BurnoutGauge (FE-13.2)", () => {
  it("renders the gauge container", () => {
    render(<BurnoutGauge score={42} />);

    expect(screen.getByTestId("burnout-gauge")).toBeInTheDocument();
  });

  it("displays the score value", () => {
    render(<BurnoutGauge score={42} />);

    const scoreEl = screen.getByTestId("burnout-score");
    expect(scoreEl).toBeInTheDocument();
    expect(scoreEl).toHaveTextContent("42");
  });

  it("shows Low risk label for score <= 30", () => {
    render(<BurnoutGauge score={20} />);

    expect(screen.getByText("Low risk")).toBeInTheDocument();
  });

  it("shows Moderate risk label for score 31-60", () => {
    render(<BurnoutGauge score={45} />);

    expect(screen.getByText("Moderate risk")).toBeInTheDocument();
  });

  it("shows High risk label for score > 60", () => {
    render(<BurnoutGauge score={75} />);

    expect(screen.getByText("High risk")).toBeInTheDocument();
  });

  it("renders the radial bar chart", () => {
    render(<BurnoutGauge score={50} />);

    expect(screen.getByTestId("radial-bar-chart")).toBeInTheDocument();
  });

  it("clamps score to 0-100 range", () => {
    const { rerender } = render(<BurnoutGauge score={150} />);

    expect(screen.getByTestId("burnout-score")).toHaveTextContent("100");

    rerender(<BurnoutGauge score={-10} />);
    expect(screen.getByTestId("burnout-score")).toHaveTextContent("0");
  });

  it("shows green color styling for low scores", () => {
    render(<BurnoutGauge score={15} />);

    const scoreEl = screen.getByTestId("burnout-score");
    const scoreSpan = scoreEl.querySelector("span");
    expect(scoreSpan?.style.color).toBe("rgb(34, 197, 94)");
  });

  it("shows red color styling for high scores", () => {
    render(<BurnoutGauge score={80} />);

    const scoreEl = screen.getByTestId("burnout-score");
    const scoreSpan = scoreEl.querySelector("span");
    expect(scoreSpan?.style.color).toBe("rgb(239, 68, 68)");
  });
});
