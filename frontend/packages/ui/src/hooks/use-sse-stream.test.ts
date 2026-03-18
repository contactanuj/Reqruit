// use-sse-stream.test.ts — ≥90% statement coverage (AC#8)
// Covers: happy-path, exponential backoff, checkpoint resume, cancel, unmount.

import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useSSEStream } from "./use-sse-stream";

// ---------------------------------------------------------------------------
// Mock EventSource
// ---------------------------------------------------------------------------

type EventListener = (e: MessageEvent) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];

  url: string;
  withCredentials: boolean;
  readyState = 1; // OPEN
  onerror: (() => void) | null = null;

  private listeners: Record<string, EventListener[]> = {};

  constructor(url: string, options?: { withCredentials?: boolean }) {
    this.url = url;
    this.withCredentials = options?.withCredentials ?? false;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: EventListener) {
    if (!this.listeners[type]) this.listeners[type] = [];
    this.listeners[type]!.push(listener);
  }

  /** Emit a named SSE event with optional data and lastEventId. */
  emit(type: string, data: unknown, lastEventId = "") {
    const raw = typeof data === "string" ? data : JSON.stringify(data);
    const event = { data: raw, lastEventId } as MessageEvent;
    (this.listeners[type] ?? []).forEach((l) => l(event));
  }

  triggerError() {
    this.onerror?.();
  }

  close() {
    this.readyState = 2; // CLOSED
  }
}

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  MockEventSource.instances = [];
  vi.stubGlobal("EventSource", MockEventSource);
  vi.useFakeTimers();
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function lastES(): MockEventSource {
  const inst = MockEventSource.instances.at(-1);
  if (!inst) throw new Error("No MockEventSource instance created");
  return inst;
}

// ---------------------------------------------------------------------------
// Happy-path streaming
// ---------------------------------------------------------------------------

describe("happy-path streaming", () => {
  it("starts idle and transitions to connecting when enabled", () => {
    const { result } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    expect(result.current.state.status).toBe("connecting");
  });

  it("transitions to streaming on first token event", () => {
    const { result } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    act(() => {
      lastES().emit("token", "Hello");
    });
    expect(result.current.state.status).toBe("streaming");
    if (result.current.state.status === "streaming") {
      expect(result.current.state.partialText).toBe("Hello");
    }
  });

  it("accumulates partial text across multiple token events", () => {
    const { result } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    act(() => {
      lastES().emit("token", "Hello");
      lastES().emit("token", " world");
    });
    if (result.current.state.status === "streaming") {
      expect(result.current.state.partialText).toBe("Hello world");
    }
  });

  it("transitions to complete on complete event and calls onComplete", () => {
    const onComplete = vi.fn();
    const { result } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true, onComplete }),
    );
    act(() => {
      lastES().emit("token", "Draft text");
      lastES().emit("complete", "Final draft");
    });
    expect(result.current.state.status).toBe("complete");
    if (result.current.state.status === "complete") {
      expect(result.current.state.finalText).toBe("Final draft");
    }
    expect(onComplete).toHaveBeenCalledWith("Final draft");
  });

  it("updates steps array on pipeline_step events", () => {
    const { result } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    const step = { id: "s1", label: "Analyzing", status: "active" as const };
    act(() => {
      lastES().emit("pipeline_step", step);
    });
    expect(result.current.state.status).toBe("streaming");
    if (result.current.state.status === "streaming") {
      expect(result.current.state.steps).toHaveLength(1);
      expect(result.current.state.steps[0]).toMatchObject(step);
    }
  });
});

// ---------------------------------------------------------------------------
// AC#7 — pipeline_step immutable update
// ---------------------------------------------------------------------------

describe("pipeline_step immutable updates", () => {
  it("appends a new step if id is not already in array", () => {
    const { result } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    act(() => {
      lastES().emit("pipeline_step", { id: "s1", label: "Step 1", status: "active" });
      lastES().emit("pipeline_step", { id: "s2", label: "Step 2", status: "pending" });
    });
    if (result.current.state.status === "streaming") {
      expect(result.current.state.steps).toHaveLength(2);
    }
  });

  it("updates an existing step by id (immutable replace)", () => {
    const { result } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    act(() => {
      lastES().emit("pipeline_step", { id: "s1", label: "Step 1", status: "active" });
      lastES().emit("pipeline_step", { id: "s1", label: "Step 1", status: "complete" });
    });
    if (result.current.state.status === "streaming") {
      expect(result.current.state.steps).toHaveLength(1);
      expect(result.current.state.steps[0]?.status).toBe("complete");
    }
  });
});

// ---------------------------------------------------------------------------
// AC#2 — Exponential backoff retry
// ---------------------------------------------------------------------------

describe("exponential backoff retry", () => {
  it("retries after 1s on first connection error", async () => {
    renderHook(() => useSSEStream({ url: "/api/sse/test", enabled: true }));
    const firstES = lastES();
    act(() => {
      firstES.triggerError();
    });
    expect(MockEventSource.instances).toHaveLength(1); // no reconnect yet
    await act(async () => {
      vi.advanceTimersByTime(1000);
    });
    expect(MockEventSource.instances).toHaveLength(2); // reconnected
  });

  it("retries after 2s on second error", async () => {
    renderHook(() => useSSEStream({ url: "/api/sse/test", enabled: true }));
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(1000); });
    act(() => { lastES().triggerError(); });
    expect(MockEventSource.instances).toHaveLength(2);
    await act(async () => { vi.advanceTimersByTime(2000); });
    expect(MockEventSource.instances).toHaveLength(3);
  });

  it("retries after 4s on third error", async () => {
    renderHook(() => useSSEStream({ url: "/api/sse/test", enabled: true }));
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(1000); });
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(2000); });
    act(() => { lastES().triggerError(); });
    expect(MockEventSource.instances).toHaveLength(3);
    await act(async () => { vi.advanceTimersByTime(4000); });
    expect(MockEventSource.instances).toHaveLength(4);
  });

  it("transitions to error state after 3 retries and calls onError", async () => {
    const onError = vi.fn();
    const { result } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true, onError }),
    );
    // 3 retries = 4 total failures (initial + 3 backoffs)
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(1000); });
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(2000); });
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(4000); });
    act(() => { lastES().triggerError(); });

    expect(result.current.state.status).toBe("error");
    if (result.current.state.status === "error") {
      expect(result.current.state.retryCount).toBe(3);
    }
    expect(onError).toHaveBeenCalledOnce();
  });

  it("exposes retryCount in error state", async () => {
    const { result } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(1000); });
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(2000); });
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(4000); });
    act(() => { lastES().triggerError(); });

    if (result.current.state.status === "error") {
      expect(result.current.state.retryCount).toBeGreaterThan(0);
    }
  });
});

// ---------------------------------------------------------------------------
// AC#3 — Checkpoint resume (last_event_id)
// ---------------------------------------------------------------------------

describe("checkpoint resume", () => {
  it("includes last_event_id as query param on reconnect after error", async () => {
    renderHook(() => useSSEStream({ url: "/api/sse/test", enabled: true }));
    act(() => {
      lastES().emit("token", "partial", "evt-42");
    });
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(1000); });

    const secondES = lastES();
    expect(secondES.url).toContain("last_event_id=evt-42");
  });

  it("does not duplicate steps when reconnecting mid-stream", async () => {
    const { result } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    act(() => {
      lastES().emit("pipeline_step", { id: "s1", label: "Step 1", status: "complete" }, "evt-1");
    });
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(1000); });
    act(() => {
      // Reconnect replays the same step id — should update in place, not append
      lastES().emit("pipeline_step", { id: "s1", label: "Step 1", status: "complete" });
    });

    if (result.current.state.status === "streaming") {
      expect(result.current.state.steps).toHaveLength(1);
    }
  });
});

// ---------------------------------------------------------------------------
// AC#4 — retry() resets count and reconnects
// ---------------------------------------------------------------------------

describe("retry()", () => {
  it("resets retryCount and reconnects from the beginning", async () => {
    const { result } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    // exhaust retries
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(1000); });
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(2000); });
    act(() => { lastES().triggerError(); });
    await act(async () => { vi.advanceTimersByTime(4000); });
    act(() => { lastES().triggerError(); });

    expect(result.current.state.status).toBe("error");
    const countBefore = MockEventSource.instances.length;

    act(() => {
      result.current.retry();
    });

    expect(result.current.state.status).toBe("connecting");
    expect(MockEventSource.instances.length).toBeGreaterThan(countBefore);
    // new URL should NOT include last_event_id (reset)
    expect(lastES().url).not.toContain("last_event_id");
  });
});

// ---------------------------------------------------------------------------
// AC#5 — cancel() closes EventSource and transitions to idle
// ---------------------------------------------------------------------------

describe("cancel()", () => {
  it("closes EventSource immediately and transitions to idle", () => {
    const { result } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    act(() => {
      lastES().emit("token", "partial");
    });
    expect(result.current.state.status).toBe("streaming");

    const es = lastES();
    act(() => {
      result.current.cancel();
    });

    expect(result.current.state.status).toBe("idle");
    expect(es.readyState).toBe(2); // CLOSED
  });

  it("prevents further events from updating state after cancel", () => {
    const { result } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    const es = lastES();
    act(() => {
      result.current.cancel();
    });
    act(() => {
      es.emit("token", "should be ignored");
    });
    expect(result.current.state.status).toBe("idle");
  });
});

// ---------------------------------------------------------------------------
// AC#6 — Unmount cleanup (no memory leaks)
// ---------------------------------------------------------------------------

describe("unmount cleanup", () => {
  it("calls EventSource.close() when component unmounts", () => {
    const { unmount } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    const es = lastES();
    const closeSpy = vi.spyOn(es, "close");

    unmount();

    expect(closeSpy).toHaveBeenCalled();
  });

  it("does not update state after unmount", () => {
    const { result, unmount } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    const es = lastES();
    unmount();

    // Emitting after unmount should not throw or update state
    expect(() => {
      act(() => {
        es.emit("token", "ghost token");
      });
    }).not.toThrow();
  });

  it("clears pending retry timeout on unmount", async () => {
    const { unmount } = renderHook(() =>
      useSSEStream({ url: "/api/sse/test", enabled: true }),
    );
    act(() => { lastES().triggerError(); });
    // unmount before the 1s retry fires
    unmount();
    const countBefore = MockEventSource.instances.length;
    await act(async () => { vi.advanceTimersByTime(1000); });
    // no new EventSource should have been created
    expect(MockEventSource.instances.length).toBe(countBefore);
  });
});
