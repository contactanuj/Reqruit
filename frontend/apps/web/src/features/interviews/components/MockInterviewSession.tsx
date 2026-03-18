"use client";

// MockInterviewSession.tsx — FE-11.4: Active mock interview session UI
// Reads all state from Zustand stores (interview-store + stream-store).

import { useState, useEffect } from "react";
import DOMPurify from "dompurify";
import { useInterviewStore } from "../store/interview-store";
import { useStreamStore } from "@/features/applications/store/stream-store";
import { useSubmitAnswer } from "../hooks/useMockInterview";

export function MockInterviewSession() {
  const [answer, setAnswer] = useState("");

  const activeSessionId = useInterviewStore((s) => s.activeSessionId);
  const currentQuestionIndex = useInterviewStore((s) => s.currentQuestionIndex);
  const totalQuestions = useInterviewStore((s) => s.totalQuestions);
  const sessionStatus = useInterviewStore((s) => s.sessionStatus);

  const streamingBuffer = useStreamStore((s) => s.streamingBuffer);
  const isStreamComplete = useStreamStore((s) => s.isComplete);

  const { mutate: submitAnswer, isPending: isSubmitting } =
    useSubmitAnswer(activeSessionId);

  // Navigation guard during active session
  const isActive = sessionStatus === "active" || sessionStatus === "in_progress";
  useEffect(() => {
    if (!isActive) return;

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isActive]);

  const handleSubmit = () => {
    if (!answer.trim() || isSubmitting) return;
    submitAnswer({ answer: answer.trim() });
    setAnswer("");
  };

  // Session complete state
  if (sessionStatus === "complete") {
    return (
      <div data-testid="mock-session" className="flex flex-col items-center gap-4 py-12">
        <p
          data-testid="session-complete"
          className="text-lg font-semibold text-foreground"
        >
          Session complete — view transcript
        </p>
      </div>
    );
  }

  const sanitizedQuestion = DOMPurify.sanitize(streamingBuffer);

  return (
    <div data-testid="mock-session" className="flex flex-col gap-6">
      {/* Progress indicator */}
      <p
        data-testid="question-progress"
        className="text-sm font-medium text-muted-foreground"
      >
        Question {currentQuestionIndex + 1} of {totalQuestions}
      </p>

      {/* AI question — streamed text */}
      <div
        data-testid="question-text"
        aria-live="polite"
        className="min-h-[4rem] rounded-lg border border-border bg-card p-4 text-sm text-foreground"
        dangerouslySetInnerHTML={{ __html: sanitizedQuestion }}
      />

      {/* Answer textarea */}
      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium text-foreground">Your answer</span>
        <textarea
          data-testid="answer-textarea"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Type your answer here..."
          rows={6}
          className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </label>

      {/* Submit button */}
      <button
        type="button"
        onClick={handleSubmit}
        disabled={!answer.trim() || isSubmitting || !isStreamComplete}
        data-testid="submit-answer-button"
        className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center self-start rounded-md bg-primary px-6 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isSubmitting ? "Submitting..." : "Submit answer"}
      </button>
    </div>
  );
}
