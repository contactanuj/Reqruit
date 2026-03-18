// use-sse-stream.ts — shared SSE hook for all 5 AI generation workflows
// ARCH-15 / Rule 7: This is the ONLY way to consume SSE in feature code.
// Consumers: cover letter, outreach, interview coaching, negotiation, career plan.

import { useReducer, useRef, useCallback, useEffect } from "react";
import type { SSEStreamState, PipelineStep, HITLDraft } from "@repo/types";

/**
 * SSE Auth Strategy:
 * EventSource does NOT support custom headers (no Authorization bearer token).
 * Authentication relies on cookies via `withCredentials: true`. The backend SSE
 * endpoint must accept cookie-based auth (the httpOnly refresh/session cookie).
 *
 * Reconnect & Last-Event-ID:
 * Browser-native EventSource sends the `Last-Event-ID` header on automatic
 * reconnect, but we manage reconnects manually (close + re-open) for backoff
 * control. On manual reconnect we pass `last_event_id` as a query parameter
 * so the backend can resume from the correct checkpoint.
 */
export interface UseSSEStreamOptions {
  /** Full SSE endpoint URL. Auth via httpOnly cookie (withCredentials: true). */
  url: string;
  /** When false the hook stays idle and cleans up any open connection. */
  enabled: boolean;
  /** Called with the final text when the stream completes cleanly. */
  onComplete?: (finalText: string) => void;
  /** Called with a human-readable error string after all retries are exhausted. */
  onError?: (error: string) => void;
  /**
   * Called whenever streaming state changes — allows consumers to sync local
   * reducer state into an external store (e.g. Zustand streamStore).
   * The hook lives in packages/ui and cannot import app-level stores directly.
   */
  onStateChange?: (state: SSEStreamState) => void;
}

// ---------------------------------------------------------------------------
// State machine
// ---------------------------------------------------------------------------

type SSEAction =
  | { type: "CONNECT" }
  | { type: "PIPELINE_STEP"; step: PipelineStep }
  | { type: "TOKEN"; token: string }
  | { type: "COMPLETE"; finalText: string }
  | { type: "ERROR"; error: string; retryCount: number }
  | { type: "HITL_READY"; draft: HITLDraft }
  | { type: "CANCEL" }
  | { type: "RETRY" };

function sseReducer(state: SSEStreamState, action: SSEAction): SSEStreamState {
  switch (action.type) {
    case "CONNECT":
      return { status: "connecting" };

    case "PIPELINE_STEP": {
      const currentSteps =
        state.status === "streaming" ? state.steps : [];
      const partialText =
        state.status === "streaming" ? state.partialText : "";
      const existingIdx = currentSteps.findIndex((s) => s.id === action.step.id);
      const steps =
        existingIdx >= 0
          ? currentSteps.map((s, i) => (i === existingIdx ? action.step : s))
          : [...currentSteps, action.step];
      return { status: "streaming", steps, partialText };
    }

    case "TOKEN": {
      const currentSteps =
        state.status === "streaming" ? state.steps : [];
      const partialText =
        state.status === "streaming" ? state.partialText : "";
      return {
        status: "streaming",
        steps: currentSteps,
        partialText: partialText + action.token,
      };
    }

    case "COMPLETE": {
      const steps = state.status === "streaming" ? state.steps : [];
      return { status: "complete", steps, finalText: action.finalText };
    }

    case "HITL_READY": {
      const steps = state.status === "streaming" ? state.steps : [];
      const partialText =
        state.status === "streaming" ? state.partialText : "";
      return {
        status: "hitl_ready",
        steps,
        partialText,
        hitlDraft: action.draft,
      };
    }

    case "ERROR":
      return {
        status: "error",
        error: action.error,
        retryCount: action.retryCount,
      };

    case "CANCEL":
    case "RETRY":
      return { status: "idle" };

    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BACKOFF_DELAYS_MS = [1000, 2000, 4000] as const;
const MAX_RETRIES = 3;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useSSEStream({
  url,
  enabled,
  onComplete,
  onError,
  onStateChange,
}: UseSSEStreamOptions): {
  state: SSEStreamState;
  cancel: () => void;
  retry: () => void;
} {
  const [state, dispatch] = useReducer(sseReducer, {
    status: "idle",
  } satisfies SSEStreamState);

  const esRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const lastEventIdRef = useRef<string | null>(null);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  // Stable callback refs — avoids re-creating connect() when callbacks change
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  const onStateChangeRef = useRef(onStateChange);
  useEffect(() => {
    onCompleteRef.current = onComplete;
  });
  useEffect(() => {
    onErrorRef.current = onError;
  });
  useEffect(() => {
    onStateChangeRef.current = onStateChange;
  });

  // Sync state to external store via onStateChange callback
  useEffect(() => {
    onStateChangeRef.current?.(state);
  }, [state]);

  // Ref to self so the error handler can schedule reconnects without
  // capturing a stale closure of connect()
  const connectRef = useRef<(resetRetry?: boolean) => void>(() => undefined);

  const closeES = useCallback(() => {
    if (retryTimeoutRef.current !== null) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    esRef.current?.close();
    esRef.current = null;
  }, []);

  const connect = useCallback(
    (resetRetry = false) => {
      if (resetRetry) {
        retryCountRef.current = 0;
        lastEventIdRef.current = null;
      }
      closeES();

      // AC#3: append last_event_id as query param for checkpoint resume on
      // manual reconnect (standard EventSource sends Last-Event-ID header on
      // native reconnect, but we close and re-open for backoff control).
      let connectUrl = url;
      if (lastEventIdRef.current) {
        const sep = url.includes("?") ? "&" : "?";
        connectUrl = `${url}${sep}last_event_id=${encodeURIComponent(lastEventIdRef.current)}`;
      }

      dispatch({ type: "CONNECT" });

      const es = new EventSource(connectUrl, { withCredentials: true });
      esRef.current = es;

      es.addEventListener("pipeline_step", (e: MessageEvent) => {
        if (!isMountedRef.current || esRef.current !== es) return;
        if (e.lastEventId) lastEventIdRef.current = e.lastEventId;
        try {
          const step = JSON.parse(e.data as string) as PipelineStep;
          dispatch({ type: "PIPELINE_STEP", step });
        } catch {
          // ignore malformed JSON
        }
      });

      es.addEventListener("token", (e: MessageEvent) => {
        if (!isMountedRef.current || esRef.current !== es) return;
        if (e.lastEventId) lastEventIdRef.current = e.lastEventId;
        dispatch({ type: "TOKEN", token: e.data as string });
      });

      es.addEventListener("hitl_ready", (e: MessageEvent) => {
        if (!isMountedRef.current || esRef.current !== es) return;
        if (e.lastEventId) lastEventIdRef.current = e.lastEventId;
        try {
          const draft = JSON.parse(e.data as string) as HITLDraft;
          dispatch({ type: "HITL_READY", draft });
        } catch {
          // ignore malformed JSON
        }
      });

      // Handle server-sent error events (distinct from connection onerror)
      es.addEventListener("error", ((e: MessageEvent) => {
        if (!isMountedRef.current || esRef.current !== es) return;
        if (e.lastEventId) lastEventIdRef.current = e.lastEventId;
        let errorMsg = "Server error during streaming";
        try {
          const parsed = JSON.parse(e.data as string) as { message?: string };
          if (parsed.message) errorMsg = parsed.message;
        } catch {
          if (typeof e.data === "string" && e.data.length > 0) {
            errorMsg = e.data;
          }
        }
        es.close();
        esRef.current = null;
        dispatch({ type: "ERROR", error: errorMsg, retryCount: retryCountRef.current });
        onErrorRef.current?.(errorMsg);
      }) as EventListener);

      es.addEventListener("complete", (e: MessageEvent) => {
        if (!isMountedRef.current || esRef.current !== es) return;
        es.close();
        esRef.current = null;
        const finalText = (e.data as string) ?? "";
        dispatch({ type: "COMPLETE", finalText });
        onCompleteRef.current?.(finalText);
      });

      // AC#2: exponential backoff retry on connection error
      es.onerror = () => {
        if (!isMountedRef.current || esRef.current !== es) return;
        es.close();
        esRef.current = null;

        const attempt = retryCountRef.current;
        if (attempt < MAX_RETRIES) {
          const delay = BACKOFF_DELAYS_MS[attempt] ?? 4000;
          retryCountRef.current += 1;
          retryTimeoutRef.current = setTimeout(() => {
            if (isMountedRef.current) connectRef.current(false);
          }, delay);
        } else {
          const errorMsg = `SSE stream failed after ${MAX_RETRIES} retries`;
          dispatch({
            type: "ERROR",
            error: errorMsg,
            retryCount: retryCountRef.current,
          });
          onErrorRef.current?.(errorMsg);
        }
      };
    },
    [url, closeES],
  );

  // Keep connectRef current so error handler always calls the latest version
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  // AC#6: connect/disconnect on enabled and url changes; clean up on unmount
  useEffect(() => {
    isMountedRef.current = true;
    if (!enabled) {
      closeES();
      return;
    }
    connect(true);
    return closeES;
  }, [enabled, connect, closeES]);

  // Unmount cleanup — prevent state updates after unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      closeES();
    };
  }, [closeES]);

  // AC#5: cancel() closes connection immediately and returns to idle
  const cancel = useCallback(() => {
    closeES();
    dispatch({ type: "CANCEL" });
  }, [closeES]);

  // AC#4: retry() resets count and reconnects from scratch
  const retry = useCallback(() => {
    dispatch({ type: "RETRY" });
    if (enabled) {
      connect(true);
    }
  }, [enabled, connect]);

  return { state, cancel, retry };
}
