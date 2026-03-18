// FeatureUnlockToast.test.tsx — FE-3.3 (AC: #1, #2, #3)

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FeatureUnlockToast } from "./FeatureUnlockToast";

describe("FeatureUnlockToast", () => {
  it("renders feature name", () => {
    render(<FeatureUnlockToast featureName="Interview Prep" />);
    expect(screen.getByText("Interview Prep is now available")).toBeTruthy();
  });

  it("renders unlock title", () => {
    render(<FeatureUnlockToast featureName="Offer Analysis" />);
    expect(screen.getByText("Feature unlocked!")).toBeTruthy();
  });

  it("has aria-live=assertive for screen reader announcement (AC #3)", () => {
    render(<FeatureUnlockToast featureName="Interview Prep" />);
    const toast = screen.getByTestId("feature-unlock-toast");
    expect(toast.getAttribute("aria-live")).toBe("assertive");
  });

  it("has aria-atomic=true for complete announcement", () => {
    render(<FeatureUnlockToast featureName="Interview Prep" />);
    const toast = screen.getByTestId("feature-unlock-toast");
    expect(toast.getAttribute("aria-atomic")).toBe("true");
  });

  it("has role=status for live region", () => {
    render(<FeatureUnlockToast featureName="Interview Prep" />);
    const toast = screen.getByRole("status");
    expect(toast).toBeTruthy();
  });

  it("renders Interview Prep unlock notification (AC #1)", () => {
    render(<FeatureUnlockToast featureName="Interview Prep" />);
    expect(screen.getByText("Interview Prep is now available")).toBeTruthy();
  });

  it("renders Offer Analysis unlock notification (AC #2)", () => {
    render(<FeatureUnlockToast featureName="Offer Analysis" />);
    expect(screen.getByText("Offer Analysis is now available")).toBeTruthy();
  });
});
