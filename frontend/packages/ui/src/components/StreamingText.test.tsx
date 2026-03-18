// StreamingText.test.tsx — accessibility and rendering tests

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StreamingText } from "./StreamingText";

describe("StreamingText", () => {
  it("renders the provided text", () => {
    render(<StreamingText text="Hello world" />);
    expect(screen.getByText(/Hello world/)).toBeTruthy();
  });

  it("has aria-live='polite' and aria-atomic='false' for screen readers (UX-7)", () => {
    const { container } = render(<StreamingText text="Hello" />);
    const span = container.querySelector("span");
    expect(span?.getAttribute("aria-live")).toBe("polite");
    expect(span?.getAttribute("aria-atomic")).toBe("false");
  });

  it("does not render cursor when isStreaming is false (default)", () => {
    render(<StreamingText text="Done" />);
    expect(screen.queryByTestId("streaming-cursor")).toBeNull();
  });

  it("renders cursor element when isStreaming is true", () => {
    render(<StreamingText text="Typing..." isStreaming />);
    expect(screen.getByTestId("streaming-cursor")).toBeTruthy();
  });

  it("cursor has aria-hidden='true' (decorative — not announced to screen readers)", () => {
    render(<StreamingText text="..." isStreaming />);
    const cursor = screen.getByTestId("streaming-cursor");
    expect(cursor.getAttribute("aria-hidden")).toBe("true");
  });

  it("applies custom className to wrapper span", () => {
    const { container } = render(
      <StreamingText text="Styled" className="custom-class" />,
    );
    const span = container.querySelector("span");
    expect(span?.className).toContain("custom-class");
  });

  it("renders empty string text without errors", () => {
    const { container } = render(<StreamingText text="" isStreaming />);
    expect(container.querySelector("span")).toBeTruthy();
  });
});
