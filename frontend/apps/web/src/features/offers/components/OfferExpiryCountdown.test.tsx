// OfferExpiryCountdown.test.tsx — FE-12.5 co-located tests

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { OfferExpiryCountdown } from "./OfferExpiryCountdown";

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
// Tests
// ---------------------------------------------------------------------------

describe("OfferExpiryCountdown (FE-12.5)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // Set "now" to 2026-03-18T12:00:00Z
    vi.setSystemTime(new Date("2026-03-18T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the countdown container", () => {
    render(<OfferExpiryCountdown expiryDate="2026-03-25T12:00:00Z" />);

    expect(screen.getByTestId("offer-expiry-countdown")).toBeInTheDocument();
  });

  it("shows days and hours remaining when expiry is more than 24h away", () => {
    // 7 days from now
    render(<OfferExpiryCountdown expiryDate="2026-03-25T12:00:00Z" />);

    const text = screen.getByTestId("expiry-text");
    expect(text).toHaveTextContent("7 days 0 hours remaining");
  });

  it("shows days and hours for partial days", () => {
    // 3 days, 6 hours from now
    render(<OfferExpiryCountdown expiryDate="2026-03-21T18:00:00Z" />);

    const text = screen.getByTestId("expiry-text");
    expect(text).toHaveTextContent("3 days 6 hours remaining");
  });

  it("shows hours and minutes when less than 24h but more than 1h", () => {
    // 10 hours from now
    render(<OfferExpiryCountdown expiryDate="2026-03-18T22:00:00Z" />);

    const text = screen.getByTestId("expiry-text");
    expect(text).toHaveTextContent("10 hours 0 minutes remaining");
  });

  it("applies red styling when less than 24h remaining", () => {
    // 12 hours from now
    render(<OfferExpiryCountdown expiryDate="2026-03-19T00:00:00Z" />);

    const container = screen.getByTestId("offer-expiry-countdown");
    expect(container.className).toContain("text-red-700");
  });

  it("does not apply red styling when more than 24h remaining", () => {
    // 3 days from now
    render(<OfferExpiryCountdown expiryDate="2026-03-21T12:00:00Z" />);

    const container = screen.getByTestId("offer-expiry-countdown");
    expect(container.className).not.toContain("text-red-700");
  });

  it("shows 'Offer expired' when expiry date is in the past", () => {
    render(<OfferExpiryCountdown expiryDate="2026-03-17T12:00:00Z" />);

    const text = screen.getByTestId("expiry-text");
    expect(text).toHaveTextContent("Offer expired");
  });

  it("renders the clock icon", () => {
    render(<OfferExpiryCountdown expiryDate="2026-03-25T12:00:00Z" />);

    expect(screen.getByTestId("expiry-icon")).toBeInTheDocument();
  });

  it("shows alarm clock icon when urgent", () => {
    // 6 hours from now — urgent
    render(<OfferExpiryCountdown expiryDate="2026-03-18T18:00:00Z" />);

    const icon = screen.getByTestId("expiry-icon");
    // Alarm clock emoji: &#x23F0; = \u23F0
    expect(icon.textContent).toBe("\u23F0");
  });

  it("shows hourglass icon when not urgent", () => {
    // 7 days from now — not urgent
    render(<OfferExpiryCountdown expiryDate="2026-03-25T12:00:00Z" />);

    const icon = screen.getByTestId("expiry-icon");
    // Hourglass emoji: &#x231B; = \u231B
    expect(icon.textContent).toBe("\u231B");
  });

  it("uses singular 'day' when exactly 1 day remaining", () => {
    render(<OfferExpiryCountdown expiryDate="2026-03-19T18:00:00Z" />);

    const text = screen.getByTestId("expiry-text");
    expect(text).toHaveTextContent("1 day");
    expect(text.textContent).not.toContain("1 days");
  });
});
