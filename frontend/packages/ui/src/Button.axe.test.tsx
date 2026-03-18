import { render } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { expect, describe, it } from "vitest";
import { Button } from "./Button";

expect.extend(toHaveNoViolations);

describe("Button accessibility (jest-axe)", () => {
  it("default variant has no ARIA violations", async () => {
    const { container } = render(<Button>Submit</Button>);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("outline variant has no ARIA violations", async () => {
    const { container } = render(<Button variant="outline">Cancel</Button>);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("ghost variant has no ARIA violations", async () => {
    const { container } = render(<Button variant="ghost">Menu</Button>);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("destructive variant has no ARIA violations", async () => {
    const { container } = render(<Button variant="destructive">Delete</Button>);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("disabled button has no ARIA violations", async () => {
    const { container } = render(<Button disabled>Disabled</Button>);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("button with aria-label has no ARIA violations", async () => {
    const { container } = render(<Button aria-label="Close dialog" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
