// OnboardingPlanView.test.tsx — FE-13.1 co-located tests

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OnboardingPlanView } from "./OnboardingPlanView";
import type { OnboardingPlan } from "../types";

const MOCK_PLAN: OnboardingPlan = {
  id: "plan-1",
  roleTitle: "Senior Frontend Engineer",
  company: "Acme Corp",
  startDate: "2026-04-01",
  createdAt: "2026-03-18T00:00:00Z",
  milestones: [
    { id: "m-1", text: "Meet your team members", completed: false, phase: "days_1_30" },
    { id: "m-2", text: "Set up development environment", completed: true, phase: "days_1_30" },
    { id: "m-3", text: "Complete first code review", completed: false, phase: "days_31_60" },
    { id: "m-4", text: "Lead a sprint planning session", completed: false, phase: "days_31_60" },
    { id: "m-5", text: "Present a technical design doc", completed: false, phase: "days_61_90" },
  ],
};

describe("OnboardingPlanView (FE-13.1)", () => {
  it("renders all three phase sections", () => {
    const onToggle = vi.fn();
    render(<OnboardingPlanView plan={MOCK_PLAN} onToggleMilestone={onToggle} />);

    expect(screen.getByTestId("onboarding-plan")).toBeInTheDocument();
    expect(screen.getByTestId("phase-days_1_30")).toBeInTheDocument();
    expect(screen.getByTestId("phase-days_31_60")).toBeInTheDocument();
    expect(screen.getByTestId("phase-days_61_90")).toBeInTheDocument();
  });

  it("renders phase labels correctly", () => {
    const onToggle = vi.fn();
    render(<OnboardingPlanView plan={MOCK_PLAN} onToggleMilestone={onToggle} />);

    expect(screen.getByText("Days 1-30")).toBeInTheDocument();
    expect(screen.getByText("Days 31-60")).toBeInTheDocument();
    expect(screen.getByText("Days 61-90")).toBeInTheDocument();
  });

  it("renders milestones in correct phases", () => {
    const onToggle = vi.fn();
    render(<OnboardingPlanView plan={MOCK_PLAN} onToggleMilestone={onToggle} />);

    // Phase 1 milestones
    const phase1 = screen.getByTestId("phase-days_1_30");
    expect(phase1).toHaveTextContent("Meet your team members");
    expect(phase1).toHaveTextContent("Set up development environment");

    // Phase 2 milestones
    const phase2 = screen.getByTestId("phase-days_31_60");
    expect(phase2).toHaveTextContent("Complete first code review");

    // Phase 3 milestones
    const phase3 = screen.getByTestId("phase-days_61_90");
    expect(phase3).toHaveTextContent("Present a technical design doc");
  });

  it("renders milestone checkboxes with correct checked state", () => {
    const onToggle = vi.fn();
    render(<OnboardingPlanView plan={MOCK_PLAN} onToggleMilestone={onToggle} />);

    const checkbox1 = screen.getByTestId("milestone-checkbox-m-1") as HTMLInputElement;
    const checkbox2 = screen.getByTestId("milestone-checkbox-m-2") as HTMLInputElement;

    expect(checkbox1.checked).toBe(false);
    expect(checkbox2.checked).toBe(true);
  });

  it("calls onToggleMilestone when checkbox is clicked", async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(<OnboardingPlanView plan={MOCK_PLAN} onToggleMilestone={onToggle} />);

    await user.click(screen.getByTestId("milestone-checkbox-m-1"));
    expect(onToggle).toHaveBeenCalledWith("m-1");

    await user.click(screen.getByTestId("milestone-checkbox-m-3"));
    expect(onToggle).toHaveBeenCalledWith("m-3");

    expect(onToggle).toHaveBeenCalledTimes(2);
  });

  it("renders all milestone data-testid attributes", () => {
    const onToggle = vi.fn();
    render(<OnboardingPlanView plan={MOCK_PLAN} onToggleMilestone={onToggle} />);

    expect(screen.getByTestId("milestone-m-1")).toBeInTheDocument();
    expect(screen.getByTestId("milestone-m-2")).toBeInTheDocument();
    expect(screen.getByTestId("milestone-m-3")).toBeInTheDocument();
    expect(screen.getByTestId("milestone-m-4")).toBeInTheDocument();
    expect(screen.getByTestId("milestone-m-5")).toBeInTheDocument();
  });

  it("renders role title and company", () => {
    const onToggle = vi.fn();
    render(<OnboardingPlanView plan={MOCK_PLAN} onToggleMilestone={onToggle} />);

    expect(screen.getByText("Senior Frontend Engineer")).toBeInTheDocument();
    expect(screen.getByText(/Acme Corp/)).toBeInTheDocument();
  });

  it("applies line-through style to completed milestones", () => {
    const onToggle = vi.fn();
    render(<OnboardingPlanView plan={MOCK_PLAN} onToggleMilestone={onToggle} />);

    const completedMilestone = screen.getByTestId("milestone-m-2");
    const textSpan = completedMilestone.querySelector("span");
    expect(textSpan?.className).toContain("line-through");
  });
});
