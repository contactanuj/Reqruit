// ProjectionCard.test.tsx — FE-13.3 co-located tests

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProjectionCard } from "./ProjectionCard";
import type { PathProjection } from "../types";

// Mock DOMPurify to pass through text (safe in test environment)
vi.mock("dompurify", () => ({
  default: {
    sanitize: (text: string) => text,
  },
}));

const MOCK_PROJECTION: PathProjection = {
  roleTitle: "Engineering Manager",
  transitionMonths: 18,
  milestones: [
    { skill: "People Management", estimatedMonths: 6 },
    { skill: "Technical Strategy", estimatedMonths: 12 },
    { skill: "Stakeholder Communication", estimatedMonths: 9 },
  ],
  resources: [
    "The Manager's Path by Camille Fournier",
    "Engineering Leadership podcast",
    "Internal mentorship program",
  ],
};

const EMPTY_PROJECTION: PathProjection = {
  roleTitle: "Staff Engineer",
  transitionMonths: 24,
  milestones: [],
  resources: [],
};

describe("ProjectionCard (FE-13.3)", () => {
  it("renders projection card with role title", () => {
    render(<ProjectionCard projection={MOCK_PROJECTION} />);

    expect(screen.getByTestId("projection-card-Engineering Manager")).toBeInTheDocument();
    expect(screen.getByText("Engineering Manager")).toBeInTheDocument();
  });

  it("displays transition timeline", () => {
    render(<ProjectionCard projection={MOCK_PROJECTION} />);

    const timeline = screen.getByTestId("transition-timeline");
    expect(timeline).toBeInTheDocument();
    expect(timeline).toHaveTextContent("Estimated transition: 18 months");
  });

  it("renders all skill milestones", () => {
    render(<ProjectionCard projection={MOCK_PROJECTION} />);

    expect(screen.getByTestId("skill-milestone-0")).toBeInTheDocument();
    expect(screen.getByTestId("skill-milestone-1")).toBeInTheDocument();
    expect(screen.getByTestId("skill-milestone-2")).toBeInTheDocument();

    expect(screen.getByText("People Management")).toBeInTheDocument();
    expect(screen.getByText("Technical Strategy")).toBeInTheDocument();
    expect(screen.getByText("Stakeholder Communication")).toBeInTheDocument();
  });

  it("shows estimated months for each milestone", () => {
    render(<ProjectionCard projection={MOCK_PROJECTION} />);

    expect(screen.getByText("~6mo")).toBeInTheDocument();
    expect(screen.getByText("~12mo")).toBeInTheDocument();
    expect(screen.getByText("~9mo")).toBeInTheDocument();
  });

  it("renders resources list", () => {
    render(<ProjectionCard projection={MOCK_PROJECTION} />);

    const resourcesList = screen.getByTestId("resources-list");
    expect(resourcesList).toBeInTheDocument();

    expect(screen.getByText("The Manager's Path by Camille Fournier")).toBeInTheDocument();
    expect(screen.getByText("Engineering Leadership podcast")).toBeInTheDocument();
    expect(screen.getByText("Internal mentorship program")).toBeInTheDocument();
  });

  it("does not render milestones section when empty", () => {
    render(<ProjectionCard projection={EMPTY_PROJECTION} />);

    expect(screen.queryByText("Skill Milestones")).not.toBeInTheDocument();
  });

  it("does not render resources section when empty", () => {
    render(<ProjectionCard projection={EMPTY_PROJECTION} />);

    expect(screen.queryByTestId("resources-list")).not.toBeInTheDocument();
  });

  it("renders card with correct data-testid for role title", () => {
    render(<ProjectionCard projection={EMPTY_PROJECTION} />);

    expect(screen.getByTestId("projection-card-Staff Engineer")).toBeInTheDocument();
  });

  it("displays transition months for empty projection", () => {
    render(<ProjectionCard projection={EMPTY_PROJECTION} />);

    expect(screen.getByTestId("transition-timeline")).toHaveTextContent(
      "Estimated transition: 24 months",
    );
  });
});
