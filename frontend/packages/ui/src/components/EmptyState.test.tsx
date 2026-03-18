// EmptyState.test.tsx — FE-3.2 (AC: #1, #2, #3, #4)

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EmptyState } from "./EmptyState";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("EmptyState", () => {
  it("renders title and role=region with aria-label", () => {
    render(
      <EmptyState
        title="No jobs yet"
        aria-label="Jobs empty state"
      />,
    );
    const region = screen.getByRole("region", { name: /jobs empty state/i });
    expect(region).toBeTruthy();
    expect(screen.getByText("No jobs yet")).toBeTruthy();
  });

  it("renders description when provided", () => {
    render(
      <EmptyState
        title="No jobs yet"
        description="Start by adding a job you are interested in"
        aria-label="Jobs empty state"
      />,
    );
    expect(screen.getByText(/start by adding a job/i)).toBeTruthy();
  });

  it("renders CTA button with correct accessible name", () => {
    const onCta = vi.fn();
    render(
      <EmptyState
        title="No jobs yet"
        ctaLabel="Add your first job"
        onCta={onCta}
        aria-label="Jobs empty state"
      />,
    );
    const btn = screen.getByRole("button", { name: /add your first job/i });
    expect(btn).toBeTruthy();
  });

  it("CTA button is keyboard-focusable (not disabled)", () => {
    const onCta = vi.fn();
    render(
      <EmptyState
        title="No jobs yet"
        ctaLabel="Add your first job"
        onCta={onCta}
        aria-label="Jobs empty state"
      />,
    );
    const btn = screen.getByRole("button", { name: /add your first job/i }) as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });

  it("calls onCta when CTA button is clicked", () => {
    const onCta = vi.fn();
    render(
      <EmptyState
        title="No jobs yet"
        ctaLabel="Add your first job"
        onCta={onCta}
        aria-label="Jobs empty state"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /add your first job/i }));
    expect(onCta).toHaveBeenCalledTimes(1);
  });

  it("does not render CTA button when ctaLabel is absent", () => {
    render(
      <EmptyState
        title="No jobs yet"
        aria-label="Jobs empty state"
      />,
    );
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders illustration when provided", () => {
    render(
      <EmptyState
        title="No applications yet"
        illustration={<span data-testid="illus">icon</span>}
        aria-label="Applications empty state"
      />,
    );
    expect(screen.getByTestId("illus")).toBeTruthy();
  });

  // Jobs empty state variant (AC #1)
  it("jobs empty state variant renders correct title and CTA", () => {
    const onCta = vi.fn();
    render(
      <EmptyState
        title="No jobs yet"
        ctaLabel="Add your first job"
        onCta={onCta}
        aria-label="Jobs empty state"
      />,
    );
    expect(screen.getByText("No jobs yet")).toBeTruthy();
    expect(screen.getByRole("button", { name: /add your first job/i })).toBeTruthy();
  });

  // Applications Kanban empty state variant (AC #2)
  it("applications empty state variant renders correct title and CTA", () => {
    const onCta = vi.fn();
    render(
      <EmptyState
        title="No applications yet"
        ctaLabel="Save a job to get started"
        onCta={onCta}
        aria-label="Applications empty state"
      />,
    );
    expect(screen.getByText("No applications yet")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /save a job to get started/i }),
    ).toBeTruthy();
  });

  // Profile empty state variant (AC #3)
  it("profile empty state variant renders correct title and CTA", () => {
    const onCta = vi.fn();
    render(
      <EmptyState
        title="Upload your resume to get started"
        ctaLabel="Upload resume"
        onCta={onCta}
        aria-label="Resume upload empty state"
      />,
    );
    expect(screen.getByText("Upload your resume to get started")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: /upload resume/i }),
    ).toBeTruthy();
  });
});
