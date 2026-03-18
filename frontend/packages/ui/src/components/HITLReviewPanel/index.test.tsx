// index.test.tsx — FE-7.3 tests for HITLReviewPanel
// Note: packages/ui vitest does not have jest-dom — use standard chai matchers.

import { describe, it, expect, vi } from "vitest";
import { render, screen, within, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { HITLReviewPanel } from "./index";

expect.extend(toHaveNoViolations);

const DRAFT_CONTENT =
  "Dear Hiring Manager,\n\nI am excited to apply for the Software Engineer position at Acme Corp.\n\nBest regards,\nTest User";
const SOURCE_CONTENT =
  "We are looking for a Software Engineer with 3+ years of experience in TypeScript and React.\n\nRequirements:\n- TypeScript\n- React\n- Node.js";

function renderPanel(overrides?: Partial<React.ComponentProps<typeof HITLReviewPanel>>) {
  const onApprove = vi.fn();
  const onRevise = vi.fn();
  return {
    onApprove,
    onRevise,
    ...render(
      <HITLReviewPanel
        draftContent={DRAFT_CONTENT}
        sourceContent={SOURCE_CONTENT}
        onApprove={onApprove}
        onRevise={onRevise}
        {...overrides}
      />
    ),
  };
}

describe("HITLReviewPanel (FE-7.3)", () => {
  it("renders the panel with draft and source content", () => {
    renderPanel();
    expect(screen.getByTestId("hitl-review-panel")).toBeTruthy();
    expect(screen.getByTestId("draft-panel")).toBeTruthy();
    expect(screen.getByTestId("source-panel")).toBeTruthy();
  });

  it("shows AI draft content in the draft pane", () => {
    renderPanel();
    const pane = screen.getByTestId("draft-pane-readonly");
    expect(pane).toBeTruthy();
    expect(pane.textContent).toContain("Dear Hiring Manager");
  });

  it("shows job description in the source pane (read-only)", () => {
    renderPanel();
    const pane = screen.getByTestId("source-pane");
    expect(pane).toBeTruthy();
    expect(pane.textContent).toContain("Software Engineer with 3+");
  });

  it("renders action bar with Approve, Revise, and Edit directly buttons", () => {
    renderPanel();
    const bar = screen.getByTestId("action-bar");
    expect(within(bar).getByTestId("approve-button")).toBeTruthy();
    expect(within(bar).getByTestId("revise-button")).toBeTruthy();
    expect(within(bar).getByTestId("edit-directly-button")).toBeTruthy();
  });

  it("Approve button has min 44px height class (NFR-A5)", () => {
    renderPanel();
    const btn = screen.getByTestId("approve-button");
    expect(btn.className).toContain("min-h-[44px]");
  });

  it("Revise button has min 44px height class (NFR-A5)", () => {
    renderPanel();
    const btn = screen.getByTestId("revise-button");
    expect(btn.className).toContain("min-h-[44px]");
  });

  it("calls onApprove when Approve is clicked", async () => {
    const user = userEvent.setup();
    const { onApprove } = renderPanel();
    await user.click(screen.getByTestId("approve-button"));
    expect(onApprove).toHaveBeenCalledOnce();
  });

  it("shows revision feedback textarea when Revise is clicked", async () => {
    const user = userEvent.setup();
    renderPanel();
    await user.click(screen.getByTestId("revise-button"));
    expect(screen.getByTestId("feedback-textarea")).toBeTruthy();
    expect(screen.getByPlaceholderText("Tell me how to improve it…")).toBeTruthy();
  });

  it("calls onRevise with feedback text when submitted", async () => {
    const user = userEvent.setup();
    const { onRevise } = renderPanel();
    await user.click(screen.getByTestId("revise-button"));
    await user.type(
      screen.getByTestId("feedback-textarea"),
      "Make it more concise"
    );
    await user.click(screen.getByTestId("submit-feedback-button"));
    expect(onRevise).toHaveBeenCalledWith("Make it more concise");
  });

  it("can cancel revision feedback", async () => {
    const user = userEvent.setup();
    renderPanel();
    await user.click(screen.getByTestId("revise-button"));
    expect(screen.getByTestId("feedback-textarea")).toBeTruthy();
    await user.click(screen.getByTestId("cancel-feedback-button"));
    expect(screen.queryByTestId("feedback-textarea")).toBeNull();
  });

  it("toggles inline editing when Edit directly is clicked", async () => {
    const user = userEvent.setup();
    renderPanel();
    // Initially in read-only mode
    expect(screen.getByTestId("draft-pane-readonly")).toBeTruthy();
    await user.click(screen.getByTestId("edit-directly-button"));
    // Now in edit mode
    expect(screen.getByTestId("draft-pane-editable")).toBeTruthy();
  });

  it("tab order: action bar has Approve first, then Revise, then Edit directly", () => {
    renderPanel();
    const bar = screen.getByTestId("action-bar");
    const buttons = within(bar).getAllByRole("button");
    const testIds = buttons.map((b) => b.getAttribute("data-testid"));
    expect(testIds[0]).toBe("approve-button");
    expect(testIds[1]).toBe("revise-button");
    expect(testIds[2]).toBe("edit-directly-button");
  });

  it("panels have accessible aria-labels", () => {
    renderPanel();
    // Check the draft panel container has aria-label
    const draftPanelEl = document.querySelector('[aria-label="AI-generated cover letter"]');
    expect(draftPanelEl).toBeTruthy();
    const sourcePanelEl = document.querySelector('[aria-label="Job description"]');
    expect(sourcePanelEl).toBeTruthy();
  });
});

describe("ActionBar keyboard shortcut (FE-7.3)", () => {
  it("calls onApprove on Ctrl+Enter", async () => {
    const user = userEvent.setup();
    const onApprove = vi.fn();
    render(
      <HITLReviewPanel
        draftContent="Draft"
        sourceContent="Source"
        onApprove={onApprove}
        onRevise={vi.fn()}
      />
    );
    await user.keyboard("{Control>}{Enter}{/Control}");
    expect(onApprove).toHaveBeenCalledOnce();
  });
});

describe("HITLReviewPanel accessibility", () => {
  it("has no accessibility violations", async () => {
    const { container } = render(
      <HITLReviewPanel
        draftContent={DRAFT_CONTENT}
        sourceContent={SOURCE_CONTENT}
        onApprove={vi.fn()}
        onRevise={vi.fn()}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
