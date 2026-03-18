"use client";

// CoachingPanel.tsx — FE-11.3: AI Interview Coaching Session
// Three-phase component: input answer, streaming feedback, complete feedback.
// Uses useInterviewCoaching hook for SSE-streamed coaching sections.

import * as React from "react";
import DOMPurify from "dompurify";
import { useInterviewCoaching } from "../hooks/useInterviewCoaching";
import { useCreditsStore } from "@/features/credits/store/credits-store";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CoachingPanelProps {
  questionId: string;
  questionText: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CoachingPanel({ questionId, questionText }: CoachingPanelProps) {
  const [answer, setAnswer] = React.useState("");
  const {
    startCoaching,
    isPending,
    isStreaming,
    isComplete,
    sections,
    reset,
  } = useInterviewCoaching();

  const dailyCredits = useCreditsStore((s) => s.dailyCredits);
  const hasCredits = dailyCredits >= 1;

  const MIN_ANSWER_LENGTH = 50;

  const hasSections =
    sections.strengths || sections.areasToImprove || sections.reframeSuggestion;

  // Determine current phase
  const isInputPhase = !isPending && !isStreaming && !isComplete;
  const isStreamingPhase = isPending || isStreaming;
  const isCompletePhase = isComplete && hasSections;

  const answerTooShort = answer.trim().length > 0 && answer.trim().length < MIN_ANSWER_LENGTH;

  const handleStart = () => {
    if (!answer.trim() || answer.trim().length < MIN_ANSWER_LENGTH || !hasCredits) return;
    startCoaching({ questionId, answer: answer.trim() });
  };

  const handleReset = () => {
    reset();
    setAnswer("");
  };

  return (
    <div data-testid="coaching-panel" className="flex flex-col gap-4">
      {/* Question context */}
      <div className="rounded-md border border-border bg-muted/50 p-4">
        <p className="text-sm text-muted-foreground">Interview question:</p>
        <p className="mt-1 font-medium text-foreground">
          {DOMPurify.sanitize(questionText)}
        </p>
      </div>

      {/* ── Input Phase ── */}
      {isInputPhase && (
        <div className="space-y-4">
          <div>
            <label
              htmlFor="coaching-answer-input"
              className="mb-1 block text-sm font-medium text-foreground"
            >
              Your answer
            </label>
            <textarea
              id="coaching-answer-input"
              data-testid="answer-input"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Type your answer to the interview question here…"
              rows={6}
              aria-describedby="answer-char-count"
              className="w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            />
            <div className="flex items-center justify-between">
              <span
                id="answer-char-count"
                data-testid="char-counter"
                className={`text-xs ${
                  answerTooShort ? "text-amber-600" : "text-muted-foreground"
                }`}
              >
                {answer.trim().length}/{MIN_ANSWER_LENGTH} min characters
              </span>
            </div>
            {answerTooShort && (
              <p className="text-xs text-amber-600" role="status">
                Please write at least {MIN_ANSWER_LENGTH} characters for meaningful feedback.
              </p>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              data-testid="start-coaching-button"
              disabled={!answer.trim() || answerTooShort || !hasCredits || isPending}
              onClick={handleStart}
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Get feedback
            </button>
            {!hasCredits && (
              <span className="text-sm text-muted-foreground">
                Insufficient credits ({dailyCredits} remaining)
              </span>
            )}
          </div>
        </div>
      )}

      {/* ── Streaming Phase ── */}
      {isStreamingPhase && (
        <div
          data-testid="coaching-streaming"
          aria-live="polite"
          className="space-y-4"
        >
          <p className="text-sm text-muted-foreground">
            Analyzing your answer…
          </p>

          {sections.strengths && (
            <section data-testid="section-strengths">
              <h3 className="mb-1 text-sm font-semibold text-foreground">
                Strengths
              </h3>
              <div
                className="whitespace-pre-wrap text-sm text-foreground"
                dangerouslySetInnerHTML={{
                  __html: DOMPurify.sanitize(sections.strengths),
                }}
              />
            </section>
          )}

          {sections.areasToImprove && (
            <section data-testid="section-improvements">
              <h3 className="mb-1 text-sm font-semibold text-foreground">
                Areas to Improve
              </h3>
              <div
                className="whitespace-pre-wrap text-sm text-foreground"
                dangerouslySetInnerHTML={{
                  __html: DOMPurify.sanitize(sections.areasToImprove),
                }}
              />
            </section>
          )}

          {sections.reframeSuggestion && (
            <section data-testid="section-reframe">
              <h3 className="mb-1 text-sm font-semibold text-foreground">
                Reframe Suggestion
              </h3>
              <div
                className="whitespace-pre-wrap text-sm text-foreground"
                dangerouslySetInnerHTML={{
                  __html: DOMPurify.sanitize(sections.reframeSuggestion),
                }}
              />
            </section>
          )}
        </div>
      )}

      {/* ── Complete Phase ── */}
      {isCompletePhase && (
        <div data-testid="coaching-complete" className="space-y-4">
          <section data-testid="section-strengths">
            <h3 className="mb-1 text-sm font-semibold text-green-700 dark:text-green-400">
              Strengths
            </h3>
            <div
              className="whitespace-pre-wrap rounded-md border border-green-200 bg-green-50 p-3 text-sm text-foreground dark:border-green-800 dark:bg-green-900/20"
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(sections.strengths),
              }}
            />
          </section>

          <section data-testid="section-improvements">
            <h3 className="mb-1 text-sm font-semibold text-amber-700 dark:text-amber-400">
              Areas to Improve
            </h3>
            <div
              className="whitespace-pre-wrap rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-foreground dark:border-amber-800 dark:bg-amber-900/20"
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(sections.areasToImprove),
              }}
            />
          </section>

          <section data-testid="section-reframe">
            <h3 className="mb-1 text-sm font-semibold text-blue-700 dark:text-blue-400">
              Reframe Suggestion
            </h3>
            <div
              className="whitespace-pre-wrap rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-foreground dark:border-blue-800 dark:bg-blue-900/20"
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(sections.reframeSuggestion),
              }}
            />
          </section>

          <button
            type="button"
            data-testid="reset-button"
            onClick={handleReset}
            className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            Try another answer
          </button>
        </div>
      )}
    </div>
  );
}
