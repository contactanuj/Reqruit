// OfferOutcomeForm.test.tsx — FE-12.5 co-located tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OfferOutcomeForm } from "./OfferOutcomeForm";

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
// Helpers
// ---------------------------------------------------------------------------

const mockOnSubmit = vi.fn();

function renderForm(props: { isPending?: boolean; currentOutcome?: "accepted" | "rejected" | "withdrawn" } = {}) {
  return render(
    <OfferOutcomeForm
      offerId="offer-1"
      onSubmit={mockOnSubmit}
      isPending={props.isPending ?? false}
      currentOutcome={props.currentOutcome}
    />,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("OfferOutcomeForm (FE-12.5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the form container", () => {
    renderForm();
    expect(screen.getByTestId("offer-outcome-form")).toBeInTheDocument();
  });

  it("renders all three outcome radio options", () => {
    renderForm();

    expect(screen.getByTestId("outcome-radio-accepted")).toBeInTheDocument();
    expect(screen.getByTestId("outcome-radio-rejected")).toBeInTheDocument();
    expect(screen.getByTestId("outcome-radio-withdrawn")).toBeInTheDocument();
  });

  it("renders labels for each option", () => {
    renderForm();

    expect(screen.getByText("Accepted")).toBeInTheDocument();
    expect(screen.getByText("Rejected")).toBeInTheDocument();
    expect(screen.getByText("Withdrawn")).toBeInTheDocument();
  });

  it("renders descriptions for each option", () => {
    renderForm();

    expect(screen.getByText("You accepted this offer")).toBeInTheDocument();
    expect(screen.getByText("You declined this offer")).toBeInTheDocument();
    expect(screen.getByText("The employer withdrew the offer")).toBeInTheDocument();
  });

  it("submit button is disabled when no outcome selected", () => {
    renderForm();

    expect(screen.getByTestId("submit-outcome-button")).toBeDisabled();
  });

  it("submit button enabled after selecting an outcome", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByTestId("outcome-radio-accepted"));

    expect(screen.getByTestId("submit-outcome-button")).toBeEnabled();
  });

  it("calls onSubmit with outcome and no notes when submitted", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByTestId("outcome-radio-rejected"));
    await user.click(screen.getByTestId("submit-outcome-button"));

    expect(mockOnSubmit).toHaveBeenCalledWith("rejected", undefined);
  });

  it("calls onSubmit with outcome and notes when notes provided", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByTestId("outcome-radio-accepted"));
    await user.type(
      screen.getByTestId("outcome-notes-input"),
      "Great team, good culture fit",
    );
    await user.click(screen.getByTestId("submit-outcome-button"));

    expect(mockOnSubmit).toHaveBeenCalledWith(
      "accepted",
      "Great team, good culture fit",
    );
  });

  it("renders the notes textarea", () => {
    renderForm();

    expect(screen.getByTestId("outcome-notes-input")).toBeInTheDocument();
    expect(screen.getByTestId("outcome-notes-input")).toHaveAttribute(
      "placeholder",
      "What did you learn? What would you do differently?",
    );
  });

  it("shows 'Saving...' text when isPending", () => {
    renderForm({ isPending: true });

    expect(screen.getByTestId("submit-outcome-button")).toHaveTextContent("Saving...");
  });

  it("submit button disabled when isPending", () => {
    renderForm({ isPending: true });

    expect(screen.getByTestId("submit-outcome-button")).toBeDisabled();
  });

  it("pre-selects outcome when currentOutcome is provided", () => {
    renderForm({ currentOutcome: "withdrawn" });

    const radio = screen.getByTestId("outcome-radio-withdrawn") as HTMLInputElement;
    expect(radio.checked).toBe(true);
  });

  it("has a radiogroup with accessible label", () => {
    renderForm();

    expect(screen.getByRole("radiogroup")).toHaveAttribute(
      "aria-label",
      "Offer outcome",
    );
  });

  it("has a heading for the form", () => {
    renderForm();

    expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent(
      "Record Outcome",
    );
  });
});
