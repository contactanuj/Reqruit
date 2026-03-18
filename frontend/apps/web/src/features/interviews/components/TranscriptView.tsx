"use client";

// TranscriptView.tsx — FE-11.5: Mock Interview Transcript & Ratings
// Displays overall score, dimension ratings, expandable Q&A entries, and recommendations.

import * as React from "react";
import DOMPurify from "dompurify";
import { useTranscriptQuery } from "../hooks/useTranscript";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TranscriptViewProps {
  sessionId: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreColor(score: number): string {
  if (score >= 70) return "text-green-600";
  if (score >= 40) return "text-amber-600";
  return "text-red-600";
}

function barColor(score: number): string {
  if (score >= 70) return "bg-green-500";
  if (score >= 40) return "bg-amber-500";
  return "bg-red-500";
}

const DIMENSION_LABELS: Record<string, string> = {
  communication: "Communication",
  depth: "Depth",
  structure: "Structure",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TranscriptView({ sessionId }: TranscriptViewProps) {
  const { data, isLoading } = useTranscriptQuery(sessionId);
  const [expandedIndex, setExpandedIndex] = React.useState<number | null>(null);

  // Loading state
  if (isLoading || !data) {
    return (
      <div data-testid="transcript-view">
        <div
          data-testid="loading-state"
          className="flex items-center justify-center py-12 text-sm text-muted-foreground"
        >
          Loading transcript…
        </div>
      </div>
    );
  }

  const toggleEntry = (index: number) => {
    setExpandedIndex((prev) => (prev === index ? null : index));
  };

  return (
    <div data-testid="transcript-view" className="flex flex-col gap-6">
      {/* Overall score */}
      <div className="flex flex-col items-center gap-1">
        <span
          data-testid="overall-score"
          className={`text-5xl font-bold ${scoreColor(data.overallScore)}`}
        >
          {data.overallScore}
        </span>
        <span className="text-sm text-muted-foreground">Overall Score</span>
      </div>

      {/* Dimension ratings */}
      <div className="flex flex-col gap-3">
        {data.dimensions.map((dim) => (
          <div
            key={dim.dimension}
            data-testid={`dimension-${dim.dimension}`}
            className="flex flex-col gap-1"
          >
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">
                {DIMENSION_LABELS[dim.dimension] ?? dim.dimension}
              </span>
              <span className={`font-semibold ${scoreColor(dim.score)}`}>
                {dim.score}
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-muted">
              <div
                className={`h-2 rounded-full transition-all ${barColor(dim.score)}`}
                style={{ width: `${Math.min(dim.score, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Transcript entries */}
      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold">Transcript</h3>
        {data.entries.map((entry) => (
          <div
            key={entry.questionIndex}
            data-testid={`transcript-entry-${entry.questionIndex}`}
            className="rounded-lg border border-border bg-card"
          >
            <button
              type="button"
              onClick={() => toggleEntry(entry.questionIndex)}
              aria-expanded={expandedIndex === entry.questionIndex}
              className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-medium text-foreground hover:bg-muted/50"
            >
              <span>
                Q{entry.questionIndex + 1}:{" "}
                {DOMPurify.sanitize(entry.questionText)}
              </span>
              <span className="shrink-0 text-xs text-muted-foreground">
                {expandedIndex === entry.questionIndex ? "▲" : "▼"}
              </span>
            </button>
            {expandedIndex === entry.questionIndex && (
              <div className="border-t border-border px-4 py-3 text-sm text-muted-foreground">
                {DOMPurify.sanitize(entry.answerText)}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Recommendations */}
      {data.recommendations.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-semibold">Recommendations</h3>
          <ul
            data-testid="recommendations-list"
            className="flex flex-col gap-1.5"
          >
            {data.recommendations.map((rec, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-sm text-muted-foreground"
              >
                <span className="mt-0.5 shrink-0 text-xs">•</span>
                <span>{DOMPurify.sanitize(rec)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
