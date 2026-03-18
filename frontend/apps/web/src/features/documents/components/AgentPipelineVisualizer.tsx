"use client";

// AgentPipelineVisualizer.tsx — FE-7.2: Real-time AI pipeline progress
// Rule 7: useSSEStream from packages/ui is the ONLY way to consume SSE.
// ARCH-17: ALL streaming state lives in streamStore — no useState for stream data.

import { useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useSSEStream } from "@repo/ui/hooks/use-sse-stream";
import { StreamingText } from "@repo/ui/components/StreamingText";
import { useStreamStore } from "@/features/applications/store/stream-store";
import type { PipelineStep } from "@repo/types";

interface AgentPipelineVisualizerProps {
  threadId: string;
  /** SSE endpoint base URL. Will be suffixed with the thread stream path. */
  streamUrl: string;
  /** Called when generation completes (transitions to HITL review). */
  onComplete?: (finalText: string) => void;
  /** Called when the stream errors out (all retries exhausted). */
  onError?: (error: string) => void;
}

function StepIcon({ status }: { status: PipelineStep["status"] }) {
  if (status === "complete") {
    return (
      <span
        aria-label="complete"
        className="flex h-6 w-6 items-center justify-center rounded-full bg-green-100 text-green-700"
      >
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </span>
    );
  }
  if (status === "error") {
    return (
      <span
        aria-label="error"
        className="flex h-6 w-6 items-center justify-center rounded-full bg-red-100 text-red-700"
      >
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </span>
    );
  }
  if (status === "active") {
    return (
      <span
        aria-label="active"
        className="flex h-6 w-6 animate-spin motion-reduce:animate-none items-center justify-center rounded-full border-2 border-primary border-t-transparent"
      />
    );
  }
  // pending
  return (
    <span
      aria-label="pending"
      className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-border bg-muted"
    />
  );
}

export function AgentPipelineVisualizer({
  threadId,
  streamUrl,
  onComplete,
  onError,
}: AgentPipelineVisualizerProps) {
  const router = useRouter();
  const appendToken = useStreamStore((s) => s.appendToken);
  const setMilestone = useStreamStore((s) => s.setMilestone);
  const streamingBuffer = useStreamStore((s) => s.streamingBuffer);

  const { state, retry } = useSSEStream({
    url: streamUrl,
    enabled: !!threadId,
    onComplete: (finalText) => {
      onComplete?.(finalText);
    },
    onError: (error) => {
      onError?.(error);
    },
  });

  // Sync stream events → Zustand store (ARCH-17)
  const prevPartialTextRef = useRef("");
  useEffect(() => {
    if (state.status === "streaming") {
      // Update milestone from latest active step label
      const activeStep = state.steps.find((s) => s.status === "active");
      if (activeStep) {
        setMilestone(activeStep.label);
      }
      // Sync partial text to stream store via appendToken
      const newText = state.partialText;
      if (newText.length > prevPartialTextRef.current.length) {
        const delta = newText.slice(prevPartialTextRef.current.length);
        appendToken(delta);
      }
      prevPartialTextRef.current = newText;
    }
  }, [state, setMilestone, appendToken]);

  const steps = state.status === "streaming" || state.status === "complete"
    ? state.steps
    : [];

  const isStreaming = state.status === "streaming";

  // Navigation guard: confirm before leaving during generation (AC #5)
  // 1. Browser close / hard navigation — beforeunload (browser-default text)
  useEffect(() => {
    if (!isStreaming) return;
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isStreaming]);

  // 2. Client-side SPA navigation — intercept link clicks to show custom confirmation
  const isStreamingRef = useRef(isStreaming);
  isStreamingRef.current = isStreaming;

  useEffect(() => {
    if (!isStreaming) return;

    const handleClick = (e: MouseEvent) => {
      const anchor = (e.target as HTMLElement).closest("a");
      if (!anchor) return;
      // Only intercept same-origin navigations
      if (anchor.origin !== window.location.origin) return;
      if (!isStreamingRef.current) return;

      const confirmed = window.confirm(
        "AI generation is in progress. Are you sure you want to leave? Your progress will be lost."
      );
      if (!confirmed) {
        e.preventDefault();
        e.stopPropagation();
      }
    };

    // Intercept popstate (browser back/forward) during streaming
    const handlePopState = () => {
      if (!isStreamingRef.current) return;
      const confirmed = window.confirm(
        "AI generation is in progress. Are you sure you want to leave? Your progress will be lost."
      );
      if (!confirmed) {
        // Push the current URL back to undo the back navigation
        window.history.pushState(null, "", window.location.href);
      }
    };

    // Push a sentinel state so we can catch back-button
    window.history.pushState(null, "", window.location.href);

    document.addEventListener("click", handleClick, true);
    window.addEventListener("popstate", handlePopState);

    return () => {
      document.removeEventListener("click", handleClick, true);
      window.removeEventListener("popstate", handlePopState);
    };
  }, [isStreaming]);

  const isReconnecting = state.status === "connecting" && streamingBuffer.length > 0;
  const hasError = state.status === "error";

  return (
    <div
      className="w-full"
      data-testid="agent-pipeline-visualizer"
      aria-label="AI generation progress"
    >
      {/* Pipeline steps — vertical timeline */}
      {steps.length > 0 && (
        <ol
          className="mb-4 flex flex-col gap-3"
          aria-label="Pipeline steps"
        >
          {steps.map((step) => (
            <li
              key={step.id}
              className="flex items-start gap-3"
              data-testid={`pipeline-step-${step.id}`}
              data-status={step.status}
            >
              <StepIcon status={step.status} />
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium">{step.label}</span>
                {step.status === "active" && isReconnecting && (
                  <span
                    className="ml-2 inline-flex items-center rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-700"
                    data-testid="reconnecting-badge"
                  >
                    Reconnecting…
                  </span>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}

      {/* Streaming text area */}
      {(isStreaming || state.status === "complete") && (
        <div className="rounded-md border border-border bg-card p-4 text-sm leading-relaxed">
          <StreamingText
            text={
              state.status === "complete"
                ? state.finalText
                : state.partialText
            }
            isStreaming={isStreaming && !isReconnecting}
          />
        </div>
      )}

      {/* Screen reader live region for milestone announcements (UX-7) */}
      <div
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
        data-testid="milestone-announcer"
      >
        {steps.find((s) => s.status === "active")?.label ?? ""}
      </div>

      {/* Error state */}
      {hasError && (
        <div
          className="mt-4 flex flex-col items-center gap-3 rounded-md border border-destructive/30 bg-destructive/5 p-4 text-center"
          data-testid="sse-error-state"
        >
          <p className="text-sm text-destructive">
            Connection failed. Please try again.
          </p>
          <button
            type="button"
            onClick={retry}
            className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            data-testid="retry-button"
          >
            Retry
          </button>
        </div>
      )}

      {/* Connecting state (initial) */}
      {state.status === "connecting" && steps.length === 0 && (
        <div
          className="flex items-center gap-2 text-sm text-muted-foreground"
          data-testid="connecting-state"
        >
          <span className="h-4 w-4 animate-spin motion-reduce:animate-none rounded-full border-2 border-primary border-t-transparent" />
          Connecting to AI pipeline…
        </div>
      )}
    </div>
  );
}
