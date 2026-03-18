import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { CreditCounter } from "./CreditCounter";
import { useCreditsStore } from "../store/credits-store";

describe("CreditCounter", () => {
  beforeEach(() => {
    useCreditsStore.setState({ dailyCredits: 10 });
  });

  it("displays remaining credits", () => {
    render(<CreditCounter />);
    expect(screen.getByLabelText("10 credits remaining today")).toBeInTheDocument();
  });

  it("has aria-live polite on the counter", () => {
    render(<CreditCounter />);
    const el = screen.getByLabelText("10 credits remaining today");
    expect(el).toHaveAttribute("aria-live", "polite");
  });

  it("updates when credits change", () => {
    const { rerender } = render(<CreditCounter />);
    useCreditsStore.setState({ dailyCredits: 3 });
    rerender(<CreditCounter />);
    expect(screen.getByLabelText("3 credits remaining today")).toBeInTheDocument();
  });
});
