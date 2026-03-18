// CoachingPanel.test.tsx — FE-11.3 co-located tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DOMPurify from "dompurify";
import { CoachingPanel } from "./CoachingPanel";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const mockStartCoaching = vi.fn();
const mockReset = vi.fn();

const defaultHookReturn = {
  startCoaching: mockStartCoaching,
  isPending: false,
  isStreaming: false,
  isComplete: false,
  sections: { strengths: "", areasToImprove: "", reframeSuggestion: "" },
  reset: mockReset,
};

let hookReturnValue = { ...defaultHookReturn };

vi.mock("../hooks/useInterviewCoaching", () => ({
  useInterviewCoaching: () => hookReturnValue,
}));

vi.mock("@/features/credits/store/credits-store", () => {
  let credits = 5;
  const store = (selector: (s: { dailyCredits: number }) => number) =>
    selector({ dailyCredits: credits });
  store.setState = (state: { dailyCredits: number }) => {
    credits = state.dailyCredits;
  };
  store.getState = () => ({ dailyCredits: credits });
  return { useCreditsStore: store };
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const defaultProps = {
  questionId: "q-1",
  questionText: "Tell me about a time you led a team through a crisis.",
};

function renderPanel(props: Partial<typeof defaultProps> = {}) {
  return render(<CoachingPanel {...defaultProps} {...props} />);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CoachingPanel (FE-11.3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hookReturnValue = { ...defaultHookReturn };
  });

  // 1. Renders input phase with textarea and button
  it("renders input phase with textarea and button", () => {
    renderPanel();

    expect(screen.getByTestId("coaching-panel")).toBeInTheDocument();
    expect(screen.getByTestId("answer-input")).toBeInTheDocument();
    expect(screen.getByTestId("start-coaching-button")).toBeInTheDocument();
    expect(screen.getByTestId("start-coaching-button")).toHaveTextContent(
      "Get coaching",
    );
  });

  // 2. Start button disabled when answer is empty
  it("disables start button when answer is empty", () => {
    renderPanel();

    expect(screen.getByTestId("start-coaching-button")).toBeDisabled();
  });

  // 3. Clicking start calls startCoaching with questionId and answer
  it("calls startCoaching with questionId and answer on click", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.type(screen.getByTestId("answer-input"), "My answer text");
    await user.click(screen.getByTestId("start-coaching-button"));

    expect(mockStartCoaching).toHaveBeenCalledWith({
      questionId: "q-1",
      answer: "My answer text",
    });
  });

  // 4. Shows streaming state when isStreaming is true
  it("shows streaming state when isStreaming is true", () => {
    hookReturnValue = {
      ...defaultHookReturn,
      isStreaming: true,
      sections: { strengths: "", areasToImprove: "", reframeSuggestion: "" },
    };
    renderPanel();

    expect(screen.getByTestId("coaching-streaming")).toBeInTheDocument();
    expect(screen.getByText("Analyzing your answer…")).toBeInTheDocument();
    // Input phase should not be visible
    expect(screen.queryByTestId("answer-input")).not.toBeInTheDocument();
  });

  // 5. Shows sections as they arrive during streaming
  it("shows sections as they arrive during streaming", () => {
    hookReturnValue = {
      ...defaultHookReturn,
      isStreaming: true,
      sections: {
        strengths: "Good communication skills",
        areasToImprove: "Could add more detail",
        reframeSuggestion: "",
      },
    };
    renderPanel();

    expect(screen.getByTestId("section-strengths")).toBeInTheDocument();
    expect(screen.getByTestId("section-improvements")).toBeInTheDocument();
    expect(screen.queryByTestId("section-reframe")).not.toBeInTheDocument();
  });

  // 6. Shows complete state with all sections
  it("shows complete state with all three sections", () => {
    hookReturnValue = {
      ...defaultHookReturn,
      isComplete: true,
      sections: {
        strengths: "Excellent STAR structure",
        areasToImprove: "Quantify the impact more",
        reframeSuggestion: "Try leading with the outcome",
      },
    };
    renderPanel();

    expect(screen.getByTestId("coaching-complete")).toBeInTheDocument();
    expect(screen.getByTestId("section-strengths")).toBeInTheDocument();
    expect(screen.getByTestId("section-improvements")).toBeInTheDocument();
    expect(screen.getByTestId("section-reframe")).toBeInTheDocument();
    expect(screen.getByTestId("reset-button")).toBeInTheDocument();
    expect(screen.getByTestId("reset-button")).toHaveTextContent(
      "Try another answer",
    );
  });

  // 7. Reset button calls reset and returns to input phase
  it("reset button calls reset and returns to input phase", async () => {
    hookReturnValue = {
      ...defaultHookReturn,
      isComplete: true,
      sections: {
        strengths: "Good",
        areasToImprove: "Better",
        reframeSuggestion: "Best",
      },
    };
    const { rerender } = renderPanel();
    const user = userEvent.setup();

    await user.click(screen.getByTestId("reset-button"));

    expect(mockReset).toHaveBeenCalledOnce();

    // After reset, hook returns default (input phase)
    hookReturnValue = { ...defaultHookReturn };
    rerender(<CoachingPanel {...defaultProps} />);

    expect(screen.getByTestId("answer-input")).toBeInTheDocument();
    expect(screen.queryByTestId("coaching-complete")).not.toBeInTheDocument();
  });

  // 8. DOMPurify sanitizes section content
  it("sanitizes section content with DOMPurify", () => {
    const sanitizeSpy = vi.spyOn(DOMPurify, "sanitize");

    hookReturnValue = {
      ...defaultHookReturn,
      isComplete: true,
      sections: {
        strengths: '<script>alert("xss")</script>Good work',
        areasToImprove: "Needs improvement",
        reframeSuggestion: "Try this approach",
      },
    };
    renderPanel();

    // DOMPurify.sanitize should have been called for each section + questionText
    expect(sanitizeSpy).toHaveBeenCalled();
    // Verify it was called with the malicious strengths content
    expect(sanitizeSpy).toHaveBeenCalledWith(
      '<script>alert("xss")</script>Good work',
    );

    sanitizeSpy.mockRestore();
  });

  // 9. Coaching sections have appropriate headings
  it("coaching sections have appropriate headings for accessibility", () => {
    hookReturnValue = {
      ...defaultHookReturn,
      isComplete: true,
      sections: {
        strengths: "Strong leadership",
        areasToImprove: "Time management",
        reframeSuggestion: "Reframe as opportunity",
      },
    };
    renderPanel();

    const headings = screen.getAllByRole("heading", { level: 3 });
    const headingTexts = headings.map((h) => h.textContent);

    expect(headingTexts).toContain("Strengths");
    expect(headingTexts).toContain("Areas to Improve");
    expect(headingTexts).toContain("Reframe Suggestion");
  });

  // Streaming region has aria-live
  it("streaming region has aria-live polite for screen readers", () => {
    hookReturnValue = {
      ...defaultHookReturn,
      isStreaming: true,
    };
    renderPanel();

    expect(screen.getByTestId("coaching-streaming")).toHaveAttribute(
      "aria-live",
      "polite",
    );
  });

  // Button disabled with no credits
  it("disables start button when no credits remain", async () => {
    const { useCreditsStore } = await import(
      "@/features/credits/store/credits-store"
    );
    (useCreditsStore as unknown as { setState: (s: { dailyCredits: number }) => void }).setState({ dailyCredits: 0 });

    const user = userEvent.setup();
    const { unmount } = renderPanel();

    await user.type(screen.getByTestId("answer-input"), "My answer");
    expect(screen.getByTestId("start-coaching-button")).toBeDisabled();

    unmount();
    // Restore credits for other tests
    (useCreditsStore as unknown as { setState: (s: { dailyCredits: number }) => void }).setState({ dailyCredits: 5 });
  });
});
