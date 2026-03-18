// SprintSetupForm.test.tsx — FE-14.2 co-located tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SprintSetupForm } from "./SprintSetupForm";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const mockMutate = vi.fn();

vi.mock("../hooks/useSprints", () => ({
  useCreateSprint: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderForm(props: { onSprintCreated?: () => void } = {}) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <SprintSetupForm {...props} />
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SprintSetupForm (FE-14.2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders with one empty goal input", () => {
    renderForm();

    expect(screen.getByTestId("sprint-setup")).toBeInTheDocument();
    expect(screen.getByTestId("goal-input-0")).toBeInTheDocument();
    expect(screen.getByTestId("goal-target-0")).toBeInTheDocument();
  });

  it("add goal button is disabled when current goal is incomplete", () => {
    renderForm();

    const addBtn = screen.getByTestId("add-goal-button");
    expect(addBtn).toBeDisabled();
  });

  it("add goal button becomes enabled when current goal is valid", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByTestId("goal-input-0"), "Apply to jobs");
    await user.type(screen.getByTestId("goal-target-0"), "5");

    expect(screen.getByTestId("add-goal-button")).not.toBeDisabled();
  });

  it("adds a new goal when add button clicked", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByTestId("goal-input-0"), "Apply to jobs");
    await user.type(screen.getByTestId("goal-target-0"), "5");
    await user.click(screen.getByTestId("add-goal-button"));

    expect(screen.getByTestId("goal-input-1")).toBeInTheDocument();
    expect(screen.getByTestId("goal-target-1")).toBeInTheDocument();
  });

  it("removes a goal when remove button clicked", async () => {
    const user = userEvent.setup();
    renderForm();

    // Fill first goal and add second
    await user.type(screen.getByTestId("goal-input-0"), "Apply to jobs");
    await user.type(screen.getByTestId("goal-target-0"), "5");
    await user.click(screen.getByTestId("add-goal-button"));

    expect(screen.getByTestId("goal-input-1")).toBeInTheDocument();

    // Remove second goal
    await user.click(screen.getByTestId("remove-goal-1"));

    expect(screen.queryByTestId("goal-input-1")).not.toBeInTheDocument();
  });

  it("does not show remove button when only one goal", () => {
    renderForm();

    expect(screen.queryByTestId("remove-goal-0")).not.toBeInTheDocument();
  });

  it("start sprint button is disabled when goals are incomplete", () => {
    renderForm();

    expect(screen.getByTestId("start-sprint-button")).toBeDisabled();
  });

  it("start sprint button calls createSprint with valid goals", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByTestId("goal-input-0"), "Apply to jobs");
    await user.type(screen.getByTestId("goal-target-0"), "5");

    const startBtn = screen.getByTestId("start-sprint-button");
    expect(startBtn).not.toBeDisabled();

    await user.click(startBtn);

    expect(mockMutate).toHaveBeenCalledWith(
      {
        goals: [{ description: "Apply to jobs", targetCount: 5 }],
      },
      expect.any(Object),
    );
  });

  it("start sprint button disabled when any goal is invalid (multi-goal)", async () => {
    const user = userEvent.setup();
    renderForm();

    // Fill first goal
    await user.type(screen.getByTestId("goal-input-0"), "Apply to jobs");
    await user.type(screen.getByTestId("goal-target-0"), "5");
    await user.click(screen.getByTestId("add-goal-button"));

    // Second goal is empty — start should be disabled
    expect(screen.getByTestId("start-sprint-button")).toBeDisabled();
  });
});
