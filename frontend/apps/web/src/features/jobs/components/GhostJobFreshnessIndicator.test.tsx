// GhostJobFreshnessIndicator.test.tsx — FE-5.6 tests

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { GhostJobFreshnessIndicator } from "./GhostJobFreshnessIndicator";

expect.extend(toHaveNoViolations);

describe("GhostJobFreshnessIndicator (FE-5.6)", () => {
  it("shows 'Fresh' for staleness_score < 14", () => {
    render(
      <GhostJobFreshnessIndicator
        stalenessScore={5}
        postedAt="2026-03-12T00:00:00Z"
        locale="US"
      />
    );
    expect(screen.getByText("Fresh")).toBeInTheDocument();
    expect(screen.getByLabelText("Freshness: Fresh")).toBeInTheDocument();
  });

  it("shows 'Ageing' for staleness_score 14–30", () => {
    render(
      <GhostJobFreshnessIndicator
        stalenessScore={20}
        postedAt="2026-02-25T00:00:00Z"
        locale="US"
      />
    );
    expect(screen.getByText("Ageing")).toBeInTheDocument();
    expect(screen.getByLabelText("Freshness: Ageing")).toBeInTheDocument();
  });

  it("shows 'Stale' for staleness_score > 30", () => {
    render(
      <GhostJobFreshnessIndicator
        stalenessScore={45}
        postedAt="2026-02-01T00:00:00Z"
        locale="US"
      />
    );
    expect(screen.getByText("Stale")).toBeInTheDocument();
    expect(screen.getByLabelText("Freshness: Stale")).toBeInTheDocument();
  });

  it("always shows both dot and label text", () => {
    const { container } = render(
      <GhostJobFreshnessIndicator stalenessScore={5} locale="US" />
    );
    // The coloured dot should be in the DOM
    const dot = container.querySelector('[aria-hidden="true"]');
    expect(dot).toBeInTheDocument();
    // Label text should also be present
    expect(screen.getByText("Fresh")).toBeInTheDocument();
  });

  it("tooltip includes posted date and last verified info", () => {
    render(
      <GhostJobFreshnessIndicator
        stalenessScore={10}
        postedAt="2026-03-07T00:00:00Z"
        lastVerifiedAt="2026-03-15T00:00:00Z"
        locale="US"
      />
    );
    const indicator = screen.getByLabelText("Freshness: Fresh");
    const title = indicator.getAttribute("title");
    expect(title).toContain("Posted");
    expect(title).toContain("last verified 10 days ago");
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <GhostJobFreshnessIndicator
        stalenessScore={5}
        postedAt="2026-03-12T00:00:00Z"
        locale="US"
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
