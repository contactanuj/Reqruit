// OfferComparison.test.tsx — FE-12.3 co-located tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { OfferComparison } from "./OfferComparison";
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

const makeOffer = (overrides: Partial<ParsedOffer> = {}): ParsedOffer => ({
  id: "offer-1",
  baseSalary: { name: "Base Salary", value: 150000, confidence: "high" },
  variable: { name: "Variable", value: 20000, confidence: "medium" },
  equity: { name: "Equity", value: 50000, confidence: "low" },
  benefits: { name: "Benefits", value: 15000, confidence: "high" },
  signingBonus: { name: "Signing Bonus", value: 10000, confidence: "high" },
  totalCompensation: 245000,
  rawText: "Offer text",
  createdAt: "2026-03-15T10:00:00Z",
  ...overrides,
});

const offer1 = makeOffer({
  id: "offer-1",
  baseSalary: { name: "Base Salary", value: 150000, confidence: "high" },
  totalCompensation: 245000,
});

const offer2 = makeOffer({
  id: "offer-2",
  baseSalary: { name: "Base Salary", value: 170000, confidence: "high" },
  variable: { name: "Variable", value: 25000, confidence: "high" },
  equity: { name: "Equity", value: 40000, confidence: "medium" },
  benefits: { name: "Benefits", value: 18000, confidence: "high" },
  signingBonus: { name: "Signing Bonus", value: 5000, confidence: "high" },
  totalCompensation: 258000,
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("OfferComparison (FE-12.3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows minimum notice when fewer than 2 offers", () => {
    render(<OfferComparison offers={[offer1]} />);

    expect(screen.getByTestId("comparison-minimum-notice")).toBeInTheDocument();
    expect(screen.getByTestId("comparison-minimum-notice")).toHaveTextContent(
      "Select at least 2 offers to compare",
    );
  });

  it("renders comparison table with 2 offers", () => {
    render(<OfferComparison offers={[offer1, offer2]} />);

    expect(screen.getByTestId("offer-comparison")).toBeInTheDocument();
    // Table should exist
    const table = screen.getByRole("table");
    expect(table).toBeInTheDocument();
  });

  it("renders all component rows", () => {
    render(<OfferComparison offers={[offer1, offer2]} />);

    const rows = screen.getAllByRole("row");
    // Header row + 6 data rows (Base Salary, Variable, Equity, Benefits, Signing Bonus, Total)
    expect(rows).toHaveLength(7);
  });

  it("shows 'Best' badge on higher values", () => {
    render(<OfferComparison offers={[offer1, offer2]} />);

    // Offer 2 has higher base salary (170k vs 150k)
    expect(screen.getByTestId("best-badge-base-salary")).toBeInTheDocument();
    expect(screen.getByTestId("best-badge-base-salary")).toHaveTextContent("Best");
  });

  it("shows 'Best' badge on total compensation for the better offer", () => {
    render(<OfferComparison offers={[offer1, offer2]} />);

    // Offer 2 has higher total (258k vs 245k)
    expect(screen.getByTestId("best-badge-total-compensation")).toBeInTheDocument();
  });

  it("renders header columns for each offer", () => {
    render(<OfferComparison offers={[offer1, offer2]} />);

    expect(screen.getByText("Offer 1")).toBeInTheDocument();
    expect(screen.getByText("Offer 2")).toBeInTheDocument();
  });

  it("renders Component header in first column", () => {
    render(<OfferComparison offers={[offer1, offer2]} />);

    expect(screen.getByText("Component")).toBeInTheDocument();
  });

  it("first column cells have sticky class", () => {
    render(<OfferComparison offers={[offer1, offer2]} />);

    const table = screen.getByRole("table");
    const firstHeaderCell = table.querySelector("thead th");
    expect(firstHeaderCell?.className).toContain("sticky");
    expect(firstHeaderCell?.className).toContain("left-0");
  });

  it("displays formatted dollar values", () => {
    render(<OfferComparison offers={[offer1, offer2]} />);

    // Use toLocaleString() to match the runtime locale formatting
    expect(screen.getAllByText(`$${(150000).toLocaleString()}`).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(`$${(170000).toLocaleString()}`).length).toBeGreaterThanOrEqual(1);
  });
});
