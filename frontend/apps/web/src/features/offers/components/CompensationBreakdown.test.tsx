// CompensationBreakdown.test.tsx — FE-12.1 co-located tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import DOMPurify from "dompurify";
import { CompensationBreakdown } from "./CompensationBreakdown";
import type { ParsedOffer } from "../types";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockOffer: ParsedOffer = {
  id: "offer-1",
  baseSalary: { name: "Base Salary", value: 150000, confidence: "high", confidenceReason: "Explicitly stated" },
  variable: { name: "Variable", value: 20000, confidence: "medium", confidenceReason: "Estimated from bonus range" },
  equity: { name: "Equity", value: 50000, confidence: "low", confidenceReason: "Vesting schedule unclear" },
  benefits: { name: "Benefits", value: 15000, confidence: "high" },
  signingBonus: { name: "Signing Bonus", value: 10000, confidence: "high" },
  totalCompensation: 245000,
  rawText: "Sample offer text",
  createdAt: "2026-03-15T10:00:00Z",
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CompensationBreakdown (FE-12.1)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all compensation components", () => {
    render(<CompensationBreakdown offer={mockOffer} />);

    expect(screen.getByTestId("compensation-breakdown")).toBeInTheDocument();
    expect(screen.getByTestId("compensation-row-base-salary")).toBeInTheDocument();
    expect(screen.getByTestId("compensation-row-variable")).toBeInTheDocument();
    expect(screen.getByTestId("compensation-row-equity")).toBeInTheDocument();
    expect(screen.getByTestId("compensation-row-benefits")).toBeInTheDocument();
    expect(screen.getByTestId("compensation-row-signing-bonus")).toBeInTheDocument();
  });

  it("displays formatted dollar values for each component", () => {
    render(<CompensationBreakdown offer={mockOffer} />);

    // Use toLocaleString() to match the runtime locale formatting
    expect(screen.getByTestId("compensation-value-base-salary")).toHaveTextContent(
      `$${(150000).toLocaleString()}`,
    );
    expect(screen.getByTestId("compensation-value-variable")).toHaveTextContent(
      `$${(20000).toLocaleString()}`,
    );
    expect(screen.getByTestId("compensation-value-equity")).toHaveTextContent(
      `$${(50000).toLocaleString()}`,
    );
    expect(screen.getByTestId("compensation-value-benefits")).toHaveTextContent(
      `$${(15000).toLocaleString()}`,
    );
    expect(screen.getByTestId("compensation-value-signing-bonus")).toHaveTextContent(
      `$${(10000).toLocaleString()}`,
    );
  });

  it("shows total compensation", () => {
    render(<CompensationBreakdown offer={mockOffer} />);

    const total = screen.getByTestId("total-compensation");
    expect(total).toBeInTheDocument();
    expect(total).toHaveTextContent(`$${(245000).toLocaleString()}`);
  });

  it("shows confidence badges with correct levels", () => {
    render(<CompensationBreakdown offer={mockOffer} />);

    expect(screen.getByTestId("confidence-badge-base-salary")).toHaveTextContent("high");
    expect(screen.getByTestId("confidence-badge-variable")).toHaveTextContent("medium");
    expect(screen.getByTestId("confidence-badge-equity")).toHaveTextContent("low");
  });

  it("renders tooltip text for components with confidenceReason", () => {
    render(<CompensationBreakdown offer={mockOffer} />);

    // Tooltip element exists (hidden until hover, but in DOM)
    expect(screen.getByTestId("confidence-tooltip-base-salary")).toHaveTextContent(
      "Explicitly stated",
    );
    expect(screen.getByTestId("confidence-tooltip-variable")).toHaveTextContent(
      "Estimated from bonus range",
    );
    expect(screen.getByTestId("confidence-tooltip-equity")).toHaveTextContent(
      "Vesting schedule unclear",
    );
  });

  it("does not render tooltip when confidenceReason is absent", () => {
    render(<CompensationBreakdown offer={mockOffer} />);

    // Benefits has no confidenceReason
    expect(screen.queryByTestId("confidence-tooltip-benefits")).not.toBeInTheDocument();
  });

  it("sanitizes component names with DOMPurify", () => {
    const sanitizeSpy = vi.spyOn(DOMPurify, "sanitize");
    render(<CompensationBreakdown offer={mockOffer} />);

    expect(sanitizeSpy).toHaveBeenCalled();
    sanitizeSpy.mockRestore();
  });

  it("has a heading for the breakdown section", () => {
    render(<CompensationBreakdown offer={mockOffer} />);

    expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent(
      "Compensation Breakdown",
    );
  });
});
