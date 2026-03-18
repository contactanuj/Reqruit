"use client";

// InterviewQuestions.tsx — FE-11.2: AI Behavioral Interview Questions
// Displays AI-generated interview questions with difficulty badges and STAR story links.

import * as React from "react";
import DOMPurify from "dompurify";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import {
  useInterviewQuestionsQuery,
  useGenerateQuestions,
} from "../hooks/useInterviewQuestions";
import { useStarStoriesQuery } from "../hooks/useStarStories";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface InterviewQuestionsProps {
  applicationId: string;
}

// ---------------------------------------------------------------------------
// Difficulty badge color mapping
// ---------------------------------------------------------------------------

const DIFFICULTY_STYLES: Record<string, string> = {
  easy: "bg-green-100 text-green-800",
  medium: "bg-amber-100 text-amber-800",
  hard: "bg-red-100 text-red-800",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function InterviewQuestions({ applicationId }: InterviewQuestionsProps) {
  const { data: questions, isLoading } = useInterviewQuestionsQuery(applicationId);
  const { mutate: generateQuestions, isPending: isGenerating } =
    useGenerateQuestions(applicationId);
  const dailyCredits = useCreditsStore((s) => s.dailyCredits);
  const { data: starStories } = useStarStoriesQuery();
  const [expandedStories, setExpandedStories] = React.useState<Set<string>>(new Set());

  const toggleStories = (questionId: string) => {
    setExpandedStories((prev) => {
      const next = new Set(prev);
      if (next.has(questionId)) {
        next.delete(questionId);
      } else {
        next.add(questionId);
      }
      return next;
    });
  };

  const hasCredits = dailyCredits >= 1;

  // Loading state — initial fetch
  if (isLoading) {
    return (
      <div data-testid="interview-questions">
        <div
          data-testid="loading-state"
          className="flex items-center justify-center py-12 text-sm text-muted-foreground"
        >
          Loading questions…
        </div>
      </div>
    );
  }

  return (
    <div data-testid="interview-questions" className="flex flex-col gap-4">
      {/* Generate button */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          data-testid="generate-button"
          disabled={!hasCredits || isGenerating}
          aria-disabled={!hasCredits || isGenerating}
          onClick={() => generateQuestions()}
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isGenerating ? "Generating…" : "Generate questions"}
        </button>
        {!hasCredits && (
          <span className="text-sm text-muted-foreground">
            Insufficient credits ({dailyCredits} remaining)
          </span>
        )}
      </div>

      {/* Generating state overlay */}
      {isGenerating && (
        <div
          data-testid="generating-state"
          className="flex items-center justify-center py-8 text-sm text-muted-foreground"
        >
          Generating interview questions…
        </div>
      )}

      {/* Empty state */}
      {!isGenerating && (!questions || questions.length === 0) && (
        <p
          data-testid="empty-state"
          className="py-8 text-center text-sm text-muted-foreground"
        >
          No questions yet — generate some!
        </p>
      )}

      {/* Question cards */}
      {!isGenerating && questions && questions.length > 0 && (
        <ul className="flex flex-col gap-3">
          {questions.map((q) => (
            <li
              key={q.id}
              data-testid={`question-card-${q.id}`}
              className="rounded-lg border border-border bg-card p-4 shadow-sm"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="flex-1 text-sm text-foreground">
                  {DOMPurify.sanitize(q.text)}
                </p>
                <span
                  data-testid={`difficulty-badge-${q.id}`}
                  className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${DIFFICULTY_STYLES[q.difficulty] ?? ""}`}
                >
                  {q.difficulty}
                </span>
              </div>
              {q.linked_star_story_ids.length > 0 && (
                <div className="mt-2">
                  <button
                    type="button"
                    onClick={() => toggleStories(q.id)}
                    aria-expanded={expandedStories.has(q.id)}
                    data-testid={`toggle-stories-${q.id}`}
                    className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
                  >
                    <span className="text-[10px]">
                      {expandedStories.has(q.id) ? "\u25BC" : "\u25B6"}
                    </span>
                    {q.linked_star_story_ids.length} linked STAR{" "}
                    {q.linked_star_story_ids.length === 1 ? "story" : "stories"}
                  </button>
                  {expandedStories.has(q.id) && starStories && (
                    <ul
                      className="mt-1.5 space-y-1 border-l-2 border-primary/20 pl-3"
                      data-testid={`linked-stories-${q.id}`}
                    >
                      {q.linked_star_story_ids.map((storyId) => {
                        const story = starStories.find((s) => s.id === storyId);
                        if (!story) return null;
                        return (
                          <li
                            key={storyId}
                            className="text-xs text-muted-foreground"
                          >
                            <span className="font-medium text-foreground">
                              {DOMPurify.sanitize(story.title)}
                            </span>
                            {story.situation && (
                              <span>
                                {" "}&mdash; {DOMPurify.sanitize(
                                  story.situation.length > 80
                                    ? story.situation.slice(0, 80) + "..."
                                    : story.situation
                                )}
                              </span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
