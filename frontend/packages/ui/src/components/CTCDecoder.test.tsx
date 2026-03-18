// CTCDecoder.test.tsx — FE-5.8 tests

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { CTCDecoder } from "./CTCDecoder";

expect.extend(toHaveNoViolations);

describe("CTCDecoder (FE-5.8)", () => {
  it("renders all breakdown sections when open", () => {
    render(
      <CTCDecoder
        salaryMin={2_000_000}
        salaryMax={2_500_000}
        locale="IN"
        open={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(screen.getByText(/In-hand monthly estimate/i)).toBeTruthy();
    expect(screen.getByText(/Variable component range/i)).toBeTruthy();
    expect(screen.getByText(/Notice buyout cost estimate/i)).toBeTruthy();
    expect(screen.getByText(/Market positioning/i)).toBeTruthy();
  });

  it("does not render when open=false", () => {
    render(
      <CTCDecoder
        salaryMin={2_000_000}
        locale="IN"
        open={false}
        onClose={vi.fn()}
      />
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("calls onClose when Escape is pressed", () => {
    const onClose = vi.fn();
    render(
      <CTCDecoder
        salaryMin={2_000_000}
        locale="IN"
        open={true}
        onClose={onClose}
      />
    );
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(
      <CTCDecoder
        salaryMin={2_000_000}
        locale="IN"
        open={true}
        onClose={onClose}
      />
    );
    fireEvent.click(screen.getByLabelText(/Close CTC Breakdown/i));
    expect(onClose).toHaveBeenCalled();
  });

  it("currency values have aria-labels with full text", () => {
    render(
      <CTCDecoder
        salaryMin={1_800_000}
        salaryMax={2_200_000}
        locale="IN"
        open={true}
        onClose={vi.fn()}
      />
    );

    // Should have at least one element with aria-label containing "lakh"
    const dialog = screen.getByRole("dialog");
    const ariaLabeled = dialog.querySelectorAll("[aria-label]");
    const hasLakhLabel = Array.from(ariaLabeled).some((el) =>
      el.getAttribute("aria-label")?.includes("lakh")
    );
    expect(hasLakhLabel).toBe(true);
  });

  it("uses monospace font for currency values", () => {
    const { container } = render(
      <CTCDecoder
        salaryMin={2_000_000}
        locale="IN"
        open={true}
        onClose={vi.fn()}
      />
    );
    const monoElements = container.querySelectorAll(".font-mono");
    expect(monoElements.length).toBeGreaterThan(0);
  });

  it("shows IN locale LPA format for salary values", () => {
    render(
      <CTCDecoder
        salaryMin={2_000_000}
        locale="IN"
        open={true}
        onClose={vi.fn()}
      />
    );
    // Should show ₹ and L format for IN locale
    const dialog = screen.getByRole("dialog");
    expect(dialog.textContent).toContain("₹");
    expect(dialog.textContent).toContain("L");
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <CTCDecoder
        salaryMin={2_000_000}
        salaryMax={2_500_000}
        locale="IN"
        open={true}
        onClose={vi.fn()}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
