// StarStoryForm.test.tsx — FE-11.1 form tests

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StarStoryForm } from "./StarStoryForm";
import type { StarStory } from "../types";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const existingStory: StarStory = {
  id: "s-1",
  title: "Led migration",
  situation: "Legacy system was failing",
  task: "Plan and execute migration",
  action: "Coordinated across 3 teams",
  result: "Zero downtime migration",
  tags: ["leadership", "technical"],
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-02T00:00:00Z",
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("StarStoryForm (FE-11.1)", () => {
  // 1. Renders all form fields
  it("renders all form fields", () => {
    render(<StarStoryForm onSubmit={vi.fn()} onCancel={vi.fn()} />);

    expect(screen.getByTestId("star-story-form")).toBeInTheDocument();
    expect(screen.getByTestId("field-title")).toBeInTheDocument();
    expect(screen.getByTestId("field-situation")).toBeInTheDocument();
    expect(screen.getByTestId("field-task")).toBeInTheDocument();
    expect(screen.getByTestId("field-action")).toBeInTheDocument();
    expect(screen.getByTestId("field-result")).toBeInTheDocument();
    expect(screen.getByTestId("field-tags")).toBeInTheDocument();
    expect(screen.getByTestId("submit-button")).toBeInTheDocument();
    expect(screen.getByTestId("cancel-button")).toBeInTheDocument();
  });

  // 2. Submit disabled when required fields empty (after first submit attempt)
  it("disables submit after attempted submission with empty required fields", async () => {
    const user = userEvent.setup();
    render(<StarStoryForm onSubmit={vi.fn()} onCancel={vi.fn()} />);

    // Click submit with all fields empty to trigger validation
    await user.click(screen.getByTestId("submit-button"));

    expect(screen.getByTestId("submit-button")).toBeDisabled();
  });

  // 3. Submitting calls onSubmit with correct data
  it("calls onSubmit with correct data on valid submission", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<StarStoryForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await user.type(screen.getByTestId("field-title"), "Led migration");
    await user.type(screen.getByTestId("field-situation"), "Legacy system");
    await user.type(screen.getByTestId("field-task"), "Plan migration");
    await user.type(screen.getByTestId("field-action"), "Coordinated teams");
    await user.type(screen.getByTestId("field-result"), "Zero downtime");
    await user.type(screen.getByTestId("field-tags"), "leadership, technical");

    await user.click(screen.getByTestId("submit-button"));

    expect(onSubmit).toHaveBeenCalledWith({
      title: "Led migration",
      situation: "Legacy system",
      task: "Plan migration",
      action: "Coordinated teams",
      result: "Zero downtime",
      tags: ["leadership", "technical"],
    });
  });

  // 4. Pre-fills fields when editing existing story
  it("pre-fills fields when editing an existing story", () => {
    render(
      <StarStoryForm
        story={existingStory}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByTestId("field-title")).toHaveValue("Led migration");
    expect(screen.getByTestId("field-situation")).toHaveValue(
      "Legacy system was failing",
    );
    expect(screen.getByTestId("field-task")).toHaveValue(
      "Plan and execute migration",
    );
    expect(screen.getByTestId("field-action")).toHaveValue(
      "Coordinated across 3 teams",
    );
    expect(screen.getByTestId("field-result")).toHaveValue(
      "Zero downtime migration",
    );
    expect(screen.getByTestId("field-tags")).toHaveValue(
      "leadership, technical",
    );
  });

  // 5. Cancel calls onCancel
  it("calls onCancel when cancel button is clicked", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<StarStoryForm onSubmit={vi.fn()} onCancel={onCancel} />);

    await user.click(screen.getByTestId("cancel-button"));

    expect(onCancel).toHaveBeenCalledOnce();
  });

  // 6. Shows validation errors for empty required fields
  it("shows validation errors when submitting with empty required fields", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<StarStoryForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await user.click(screen.getByTestId("submit-button"));

    const errors = screen.getAllByTestId("validation-error");
    expect(errors).toHaveLength(5);
    expect(errors[0]).toHaveTextContent("Title is required");
    expect(errors[1]).toHaveTextContent("Situation is required");
    expect(errors[2]).toHaveTextContent("Task is required");
    expect(errors[3]).toHaveTextContent("Action is required");
    expect(errors[4]).toHaveTextContent("Result is required");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  // 7. Tags field splits comma-separated values into array
  it("splits comma-separated tags into array", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<StarStoryForm onSubmit={onSubmit} onCancel={vi.fn()} />);

    await user.type(screen.getByTestId("field-title"), "Story");
    await user.type(screen.getByTestId("field-situation"), "Situation");
    await user.type(screen.getByTestId("field-task"), "Task");
    await user.type(screen.getByTestId("field-action"), "Action");
    await user.type(screen.getByTestId("field-result"), "Result");
    await user.type(
      screen.getByTestId("field-tags"),
      "leadership, teamwork,  conflict resolution ,",
    );

    await user.click(screen.getByTestId("submit-button"));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        tags: ["leadership", "teamwork", "conflict resolution"],
      }),
    );
  });
});
