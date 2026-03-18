// MockInterviewSetup.test.tsx — FE-11.4 co-located tests

import { describe, it, expect, vi, beforeEach, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MockInterviewSetup } from "./MockInterviewSetup";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { useStreamStore } from "@/features/applications/store/stream-store";
import { useInterviewStore } from "../store/interview-store";

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

// ---------------------------------------------------------------------------
// MSW Handlers
// ---------------------------------------------------------------------------

const START_URL = "http://localhost:8000/interview/mock-sessions";

const server = setupServer(
  http.post(START_URL, () =>
    HttpResponse.json({
      session_id: "sess-123",
      thread_id: "thread-456",
      total_questions: 5,
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
  useCreditsStore.setState({ dailyCredits: 5 });
  useStreamStore.getState().reset();
  useInterviewStore.getState().resetSession();
});

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

function renderSetup(props: { onSessionStart?: () => void } = {}) {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <MockInterviewSetup onSessionStart={props.onSessionStart} />
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("MockInterviewSetup (FE-11.4)", () => {
  beforeEach(() => {
    useCreditsStore.setState({ dailyCredits: 5 });
  });

  // 1. Renders type and duration radio options
  it("renders type and duration radio options", () => {
    renderSetup();

    expect(screen.getByTestId("mock-setup")).toBeInTheDocument();
    expect(screen.getByTestId("type-behavioral")).toBeInTheDocument();
    expect(screen.getByTestId("type-technical")).toBeInTheDocument();
    expect(screen.getByTestId("type-system_design")).toBeInTheDocument();
    expect(screen.getByTestId("duration-30")).toBeInTheDocument();
    expect(screen.getByTestId("duration-45")).toBeInTheDocument();
    expect(screen.getByTestId("duration-60")).toBeInTheDocument();
  });

  // 2. Default selection: behavioral + 30min
  it("defaults to behavioral type and 30 min duration", () => {
    renderSetup();

    expect(screen.getByTestId("type-behavioral")).toBeChecked();
    expect(screen.getByTestId("duration-30")).toBeChecked();

    expect(screen.getByTestId("type-technical")).not.toBeChecked();
    expect(screen.getByTestId("type-system_design")).not.toBeChecked();
    expect(screen.getByTestId("duration-45")).not.toBeChecked();
    expect(screen.getByTestId("duration-60")).not.toBeChecked();
  });

  // 3. Can change type selection
  it("can change type selection", async () => {
    const user = userEvent.setup();
    renderSetup();

    await user.click(screen.getByTestId("type-technical"));

    expect(screen.getByTestId("type-technical")).toBeChecked();
    expect(screen.getByTestId("type-behavioral")).not.toBeChecked();
  });

  // 4. Can change duration selection
  it("can change duration selection", async () => {
    const user = userEvent.setup();
    renderSetup();

    await user.click(screen.getByTestId("duration-60"));

    expect(screen.getByTestId("duration-60")).toBeChecked();
    expect(screen.getByTestId("duration-30")).not.toBeChecked();
  });

  // 5. Start button calls mutation with selected config
  it("start button calls mutation with selected config", async () => {
    const user = userEvent.setup();
    renderSetup();

    await user.click(screen.getByTestId("type-technical"));
    await user.click(screen.getByTestId("duration-45"));
    await user.click(screen.getByTestId("start-button"));

    // After success, interview store should have session data
    await waitFor(() =>
      expect(useInterviewStore.getState().activeSessionId).toBe("sess-123"),
    );

    expect(useInterviewStore.getState().sessionConfig).toEqual({
      type: "technical",
      duration: 45,
    });
    expect(useInterviewStore.getState().totalQuestions).toBe(5);
  });

  // 6. Credit decrement on start
  it("decrements credit when start is clicked", async () => {
    const user = userEvent.setup();
    useCreditsStore.setState({ dailyCredits: 3 });
    renderSetup();

    await user.click(screen.getByTestId("start-button"));

    // Optimistic decrement
    expect(useCreditsStore.getState().dailyCredits).toBe(2);
  });

  // 7. Credit revert on error
  it("reverts credit on API error", async () => {
    server.use(
      http.post(START_URL, () =>
        HttpResponse.json({ error: "fail" }, { status: 500 }),
      ),
    );
    const user = userEvent.setup();
    useCreditsStore.setState({ dailyCredits: 3 });
    renderSetup();

    await user.click(screen.getByTestId("start-button"));

    await waitFor(() =>
      expect(useCreditsStore.getState().dailyCredits).toBe(3),
    );
  });

  // 8. Start button disabled when insufficient credits
  it("disables start button when insufficient credits", () => {
    useCreditsStore.setState({ dailyCredits: 0 });
    renderSetup();

    const btn = screen.getByTestId("start-button");
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText(/Insufficient credits/)).toBeInTheDocument();
  });

  // 9. Calls onSessionStart after successful start
  it("calls onSessionStart after successful start", async () => {
    const onSessionStart = vi.fn();
    const user = userEvent.setup();
    renderSetup({ onSessionStart });

    await user.click(screen.getByTestId("start-button"));

    await waitFor(() => expect(onSessionStart).toHaveBeenCalledOnce());
  });
});
