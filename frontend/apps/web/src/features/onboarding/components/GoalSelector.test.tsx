// GoalSelector.test.tsx — FE-3.1 (AC: #1, #2, #3)

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GoalSelector } from "./GoalSelector";

const mockOnSelect = vi.fn();
const mockOnSkip = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
});

describe("GoalSelector", () => {
  it("renders all four goal cards", () => {
    render(<GoalSelector onSelect={mockOnSelect} onSkip={mockOnSkip} />);

    expect(screen.getByRole("radio", { name: /find jobs/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /interview prep/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /negotiate offer/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /track applications/i })).toBeInTheDocument();
  });

  it("uses radiogroup role for accessibility", () => {
    render(<GoalSelector onSelect={mockOnSelect} onSkip={mockOnSkip} />);
    expect(screen.getByRole("radiogroup", { name: /job search goal/i })).toBeInTheDocument();
  });

  it("each goal card has min-h-[44px] class for touch target requirement", () => {
    render(<GoalSelector onSelect={mockOnSelect} onSkip={mockOnSkip} />);
    const findJobsCard = screen.getByRole("radio", { name: /find jobs/i });
    expect(findJobsCard.className).toContain("min-h-[44px]");
    expect(findJobsCard.className).toContain("min-w-[44px]");
  });

  it("Continue button is disabled when no goal is selected", () => {
    render(<GoalSelector onSelect={mockOnSelect} onSkip={mockOnSkip} />);
    const continueBtn = screen.getByTestId("continue-button");
    expect(continueBtn).toBeDisabled();
  });

  it("selecting a goal enables the Continue button and marks card aria-checked", async () => {
    const user = userEvent.setup();
    render(<GoalSelector onSelect={mockOnSelect} onSkip={mockOnSkip} />);

    const findJobsCard = screen.getByRole("radio", { name: /find jobs/i });
    await user.click(findJobsCard);

    expect(findJobsCard).toHaveAttribute("aria-checked", "true");

    const continueBtn = screen.getByTestId("continue-button");
    expect(continueBtn).not.toBeDisabled();
  });

  it("clicking Continue calls onSelect with selected goal", async () => {
    const user = userEvent.setup();
    render(<GoalSelector onSelect={mockOnSelect} onSkip={mockOnSkip} />);

    await user.click(screen.getByRole("radio", { name: /find jobs/i }));
    await user.click(screen.getByTestId("continue-button"));

    expect(mockOnSelect).toHaveBeenCalledWith("find_jobs");
    expect(mockOnSelect).toHaveBeenCalledTimes(1);
  });

  it("clicking skip calls onSkip without requiring a selection", async () => {
    const user = userEvent.setup();
    render(<GoalSelector onSelect={mockOnSelect} onSkip={mockOnSkip} />);

    await user.click(screen.getByTestId("skip-button"));

    expect(mockOnSkip).toHaveBeenCalledTimes(1);
    expect(mockOnSelect).not.toHaveBeenCalled();
  });

  it("shows loading state when isPending is true", async () => {
    const user = userEvent.setup();
    render(<GoalSelector onSelect={mockOnSelect} onSkip={mockOnSkip} isPending />);

    await user.click(screen.getByRole("radio", { name: /interview prep/i }));

    const continueBtn = screen.getByTestId("continue-button");
    expect(continueBtn).toBeDisabled();
    expect(continueBtn).toHaveTextContent(/saving/i);
  });

  it("only one goal card is checked at a time", async () => {
    const user = userEvent.setup();
    render(<GoalSelector onSelect={mockOnSelect} onSkip={mockOnSkip} />);

    await user.click(screen.getByRole("radio", { name: /find jobs/i }));
    await user.click(screen.getByRole("radio", { name: /interview prep/i }));

    expect(screen.getByRole("radio", { name: /find jobs/i })).toHaveAttribute(
      "aria-checked",
      "false",
    );
    expect(screen.getByRole("radio", { name: /interview prep/i })).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });
});
