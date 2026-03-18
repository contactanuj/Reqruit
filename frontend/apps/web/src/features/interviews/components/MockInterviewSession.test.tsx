// MockInterviewSession.test.tsx — FE-11.4 co-located tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MockInterviewSession } from "./MockInterviewSession";
import { useInterviewStore } from "../store/interview-store";
import { useStreamStore } from "@/features/applications/store/stream-store";

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

const mockSubmitAnswer = vi.fn();

vi.mock("../hooks/useMockInterview", () => ({
  useStartSession: vi.fn(),
  useSubmitAnswer: () => ({
    mutate: mockSubmitAnswer,
    isPending: false,
  }),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderSession() {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MockInterviewSession />
    </QueryClientProvider>,
  );
}

function setActiveSession(overrides: Partial<ReturnType<typeof useInterviewStore.getState>> = {}) {
  useInterviewStore.setState({
    activeSessionId: "sess-123",
    currentQuestionIndex: 0,
    totalQuestions: 5,
    answers: [],
    sessionConfig: { type: "behavioral", duration: 30 },
    sessionStatus: "active",
    startedAt: Date.now(),
    ...overrides,
  });
}

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  useInterviewStore.getState().resetSession();
  useStreamStore.getState().reset();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("MockInterviewSession (FE-11.4)", () => {
  // 1. Shows question progress
  it("shows question progress", () => {
    setActiveSession({ currentQuestionIndex: 2, totalQuestions: 5 });
    renderSession();

    const progress = screen.getByTestId("question-progress");
    expect(progress).toBeInTheDocument();
    expect(progress).toHaveTextContent("Question 3 of 5");
  });

  // 2. Displays streaming question text
  it("displays streaming question text", () => {
    setActiveSession();
    useStreamStore.setState({
      streamingBuffer: "Tell me about a time you led a project.",
      isComplete: true,
    });

    renderSession();

    const questionText = screen.getByTestId("question-text");
    expect(questionText).toHaveTextContent(
      "Tell me about a time you led a project.",
    );
  });

  // 3. Submit button disabled when answer empty
  it("disables submit button when answer is empty", () => {
    setActiveSession();
    useStreamStore.setState({ streamingBuffer: "A question?", isComplete: true });

    renderSession();

    const btn = screen.getByTestId("submit-answer-button");
    expect(btn).toBeDisabled();
  });

  // 4. Submit calls submitAnswer mutation
  it("calls submitAnswer mutation on submit", async () => {
    const user = userEvent.setup();
    setActiveSession();
    useStreamStore.setState({
      streamingBuffer: "Tell me about a challenge.",
      isComplete: true,
    });

    renderSession();

    const textarea = screen.getByTestId("answer-textarea");
    await user.type(textarea, "I once handled a difficult deadline...");

    const btn = screen.getByTestId("submit-answer-button");
    expect(btn).not.toBeDisabled();

    await user.click(btn);

    expect(mockSubmitAnswer).toHaveBeenCalledOnce();
    expect(mockSubmitAnswer).toHaveBeenCalledWith({
      answer: "I once handled a difficult deadline...",
    });
  });

  // 5. Shows session complete state
  it("shows session complete state", () => {
    setActiveSession({ sessionStatus: "complete" });

    renderSession();

    expect(screen.getByTestId("session-complete")).toBeInTheDocument();
    expect(screen.getByTestId("session-complete")).toHaveTextContent(
      "Session complete — view transcript",
    );

    // Should not show question progress or textarea
    expect(screen.queryByTestId("question-progress")).not.toBeInTheDocument();
    expect(screen.queryByTestId("answer-textarea")).not.toBeInTheDocument();
  });

  // 6. DOMPurify sanitizes question text
  it("sanitizes question text with DOMPurify", () => {
    setActiveSession();
    useStreamStore.setState({
      streamingBuffer: '<p>Safe text</p><script>alert("xss")</script>',
      isComplete: true,
    });

    renderSession();

    const questionText = screen.getByTestId("question-text");
    expect(questionText.innerHTML).toContain("<p>Safe text</p>");
    expect(questionText.innerHTML).not.toContain("<script>");
    expect(questionText.innerHTML).not.toContain("alert");
  });
});
