// AgentPipelineVisualizer.test.tsx — FE-7.2 tests

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AgentPipelineVisualizer } from "./AgentPipelineVisualizer";
import { useStreamStore } from "@/features/applications/store/stream-store";
import type { SSEStreamState } from "@repo/types";

// ---------------------------------------------------------------------------
// Mock useSSEStream — it uses EventSource which isn't in jsdom
// ---------------------------------------------------------------------------

const mockCancel = vi.fn();
const mockRetry = vi.fn();
let mockState: SSEStreamState = { status: "idle" };

vi.mock("@repo/ui/hooks/use-sse-stream", () => ({
  useSSEStream: vi.fn(() => ({
    state: mockState,
    cancel: mockCancel,
    retry: mockRetry,
  })),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

function makeQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderVisualizer(props?: { threadId?: string; streamUrl?: string; onComplete?: (t: string) => void }) {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <AgentPipelineVisualizer
        threadId={props?.threadId ?? "thread-123"}
        streamUrl={props?.streamUrl ?? "http://localhost:8000/stream/thread-123"}
        onComplete={props?.onComplete}
      />
    </QueryClientProvider>
  );
}

describe("AgentPipelineVisualizer (FE-7.2)", () => {
  beforeEach(() => {
    mockState = { status: "idle" };
    useStreamStore.getState().reset();
    vi.clearAllMocks();
  });

  afterEach(() => {
    useStreamStore.getState().reset();
  });

  it("renders the visualizer container", () => {
    renderVisualizer();
    expect(screen.getByTestId("agent-pipeline-visualizer")).toBeInTheDocument();
  });

  it("shows connecting state when status is connecting and no steps yet", () => {
    mockState = { status: "connecting" };
    renderVisualizer();
    expect(screen.getByTestId("connecting-state")).toBeInTheDocument();
    expect(screen.getByTestId("connecting-state")).toHaveTextContent(
      "Connecting to AI pipeline"
    );
  });

  it("renders pipeline steps in sequence when streaming", () => {
    mockState = {
      status: "streaming",
      steps: [
        { id: "step-1", label: "Analysing job requirements…", status: "complete" },
        { id: "step-2", label: "Matching your experience…", status: "active" },
        { id: "step-3", label: "Writing your cover letter…", status: "pending" },
      ],
      partialText: "Dear Hiring Manager,",
    };
    renderVisualizer();

    expect(screen.getByTestId("pipeline-step-step-1")).toBeInTheDocument();
    expect(screen.getByTestId("pipeline-step-step-2")).toBeInTheDocument();
    expect(screen.getByTestId("pipeline-step-step-3")).toBeInTheDocument();
    // Steps appear in the list; use getAllByText since announcer also contains the active step label
    expect(screen.getAllByText("Analysing job requirements…").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Matching your experience…").length).toBeGreaterThanOrEqual(1);
  });

  it("shows step status icons correctly", () => {
    mockState = {
      status: "streaming",
      steps: [
        { id: "step-1", label: "Step 1", status: "complete" },
        { id: "step-2", label: "Step 2", status: "active" },
        { id: "step-3", label: "Step 3", status: "error" },
        { id: "step-4", label: "Step 4", status: "pending" },
      ],
      partialText: "",
    };
    renderVisualizer();

    expect(screen.getByLabelText("complete")).toBeInTheDocument();
    expect(screen.getByLabelText("active")).toBeInTheDocument();
    expect(screen.getByLabelText("error")).toBeInTheDocument();
    expect(screen.getByLabelText("pending")).toBeInTheDocument();
  });

  it("renders streaming text with cursor when active", () => {
    mockState = {
      status: "streaming",
      steps: [{ id: "step-1", label: "Writing…", status: "active" }],
      partialText: "I am excited to apply for",
    };
    renderVisualizer();

    expect(screen.getByText(/I am excited to apply for/)).toBeInTheDocument();
    expect(screen.getByTestId("streaming-cursor")).toBeInTheDocument();
  });

  it("shows Retry button in error state after exhausted retries", async () => {
    mockState = { status: "error", error: "SSE stream failed after 3 retries", retryCount: 3 };
    renderVisualizer();

    expect(screen.getByTestId("retry-button")).toBeInTheDocument();
    expect(screen.getByTestId("sse-error-state")).toBeInTheDocument();
  });

  it("calls retry() when Retry button is clicked", async () => {
    const user = userEvent.setup();
    mockState = { status: "error", error: "Connection failed", retryCount: 3 };
    renderVisualizer();

    await user.click(screen.getByTestId("retry-button"));
    expect(mockRetry).toHaveBeenCalledOnce();
  });

  it("has aria-live assertive region for milestone announcements", () => {
    mockState = {
      status: "streaming",
      steps: [
        { id: "step-1", label: "Analysing job requirements…", status: "active" },
      ],
      partialText: "",
    };
    renderVisualizer();

    const announcer = screen.getByTestId("milestone-announcer");
    expect(announcer).toHaveAttribute("aria-live", "assertive");
    expect(announcer).toHaveTextContent("Analysing job requirements…");
  });

  it("stream state (milestone) is updated in Zustand streamStore, not component state", () => {
    mockState = {
      status: "streaming",
      steps: [
        { id: "step-1", label: "Analysing job requirements…", status: "active" },
      ],
      partialText: "",
    };
    renderVisualizer();

    // After render + useEffect, milestone should be in Zustand
    // Note: we check it after act to allow effects to run
    act(() => {});
    expect(useStreamStore.getState().milestoneLabel).toBe(
      "Analysing job requirements…"
    );
  });

  it("calls onComplete callback when stream completes", async () => {
    const onComplete = vi.fn();
    const { useSSEStream } = await import("@repo/ui/hooks/use-sse-stream");
    const mockUseSSEStream = vi.mocked(useSSEStream);

    // Simulate onComplete being called by the hook
    mockState = {
      status: "complete",
      steps: [{ id: "step-1", label: "Done", status: "complete" }],
      finalText: "Final cover letter text",
    };

    // Re-mock to trigger onComplete immediately
    mockUseSSEStream.mockImplementationOnce(({ onComplete: cb }) => {
      cb?.("Final cover letter text");
      return { state: mockState, cancel: mockCancel, retry: mockRetry };
    });

    renderVisualizer({ onComplete });
    expect(onComplete).toHaveBeenCalledWith("Final cover letter text");
  });
});
