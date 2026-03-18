// InterviewQuestions.test.tsx — FE-11.2 co-located tests

import { describe, it, expect, vi, beforeEach, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { InterviewQuestions } from "./InterviewQuestions";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import type { InterviewQuestion } from "../types";

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
// Test data
// ---------------------------------------------------------------------------

const MOCK_QUESTIONS: InterviewQuestion[] = [
  {
    id: "q-1",
    text: "Tell me about a time you resolved a conflict in your team.",
    difficulty: "easy",
    linked_star_story_ids: ["star-1"],
  },
  {
    id: "q-2",
    text: "Describe a situation where you had to make a decision with incomplete information.",
    difficulty: "medium",
    linked_star_story_ids: ["star-2", "star-3"],
  },
  {
    id: "q-3",
    text: "Walk me through a time you failed and what you learned from it.",
    difficulty: "hard",
    linked_star_story_ids: [],
  },
];

// ---------------------------------------------------------------------------
// MSW Handlers
// ---------------------------------------------------------------------------

const QUESTIONS_URL = "http://localhost:8000/applications/:id/interview-questions";
const GENERATE_URL = "http://localhost:8000/applications/:id/interview-questions/generate";

const server = setupServer(
  http.get(QUESTIONS_URL, () => HttpResponse.json(MOCK_QUESTIONS)),
  http.post(GENERATE_URL, () => HttpResponse.json(MOCK_QUESTIONS)),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
  useCreditsStore.setState({ dailyCredits: 10 });
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

function renderComponent(props: { applicationId?: string } = {}) {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <InterviewQuestions applicationId={props.applicationId ?? "app-1"} />
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("InterviewQuestions (FE-11.2)", () => {
  beforeEach(() => {
    useCreditsStore.setState({ dailyCredits: 10 });
  });

  // 1. Renders loading state
  it("renders loading state while fetching", () => {
    // Make the server delay so we can see loading state
    server.use(
      http.get(QUESTIONS_URL, async () => {
        await new Promise((resolve) => setTimeout(resolve, 5000));
        return HttpResponse.json(MOCK_QUESTIONS);
      }),
    );

    renderComponent();
    expect(screen.getByTestId("loading-state")).toBeInTheDocument();
    expect(screen.getByTestId("loading-state")).toHaveTextContent("Loading questions");
  });

  // 2. Renders questions after fetch
  it("renders question cards after fetch completes", async () => {
    renderComponent();

    await waitFor(() =>
      expect(screen.getByTestId("question-card-q-1")).toBeInTheDocument(),
    );

    expect(screen.getByTestId("question-card-q-2")).toBeInTheDocument();
    expect(screen.getByTestId("question-card-q-3")).toBeInTheDocument();
    expect(screen.getByText(/Tell me about a time you resolved/)).toBeInTheDocument();
    expect(screen.getByText("1 linked STAR story")).toBeInTheDocument();
    expect(screen.getByText("2 linked STAR stories")).toBeInTheDocument();
  });

  // 3. Shows empty state when no questions
  it("shows empty state when no questions returned", async () => {
    server.use(http.get(QUESTIONS_URL, () => HttpResponse.json([])));

    renderComponent();

    await waitFor(() =>
      expect(screen.getByTestId("empty-state")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("empty-state")).toHaveTextContent(
      "No questions yet — generate some!",
    );
  });

  // 4. Generate button triggers mutation
  it("generate button calls mutation on click", async () => {
    server.use(http.get(QUESTIONS_URL, () => HttpResponse.json([])));
    const user = userEvent.setup();

    renderComponent();

    await waitFor(() =>
      expect(screen.getByTestId("generate-button")).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId("generate-button"));

    // After mutation succeeds, questions should appear
    await waitFor(() =>
      expect(screen.getByTestId("question-card-q-1")).toBeInTheDocument(),
    );
  });

  // 5. Shows generating state during mutation
  it("shows generating state during mutation", async () => {
    server.use(
      http.get(QUESTIONS_URL, () => HttpResponse.json([])),
      http.post(GENERATE_URL, async () => {
        await new Promise((resolve) => setTimeout(resolve, 5000));
        return HttpResponse.json(MOCK_QUESTIONS);
      }),
    );
    const user = userEvent.setup();

    renderComponent();

    await waitFor(() =>
      expect(screen.getByTestId("generate-button")).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId("generate-button"));

    await waitFor(() =>
      expect(screen.getByTestId("generating-state")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("generating-state")).toHaveTextContent(
      "Generating interview questions",
    );
    expect(screen.getByTestId("generate-button")).toHaveTextContent("Generating…");
  });

  // 6. Difficulty badges have correct colors/text
  it("renders difficulty badges with correct colors and text", async () => {
    renderComponent();

    await waitFor(() =>
      expect(screen.getByTestId("difficulty-badge-q-1")).toBeInTheDocument(),
    );

    const easyBadge = screen.getByTestId("difficulty-badge-q-1");
    const mediumBadge = screen.getByTestId("difficulty-badge-q-2");
    const hardBadge = screen.getByTestId("difficulty-badge-q-3");

    expect(easyBadge).toHaveTextContent("easy");
    expect(easyBadge.className).toContain("bg-green-100");
    expect(easyBadge.className).toContain("text-green-800");

    expect(mediumBadge).toHaveTextContent("medium");
    expect(mediumBadge.className).toContain("bg-amber-100");
    expect(mediumBadge.className).toContain("text-amber-800");

    expect(hardBadge).toHaveTextContent("hard");
    expect(hardBadge.className).toContain("bg-red-100");
    expect(hardBadge.className).toContain("text-red-800");
  });

  // 7. Credit decrement on generate
  it("decrements credit when generate is clicked", async () => {
    server.use(http.get(QUESTIONS_URL, () => HttpResponse.json([])));
    const user = userEvent.setup();
    useCreditsStore.setState({ dailyCredits: 5 });

    renderComponent();

    await waitFor(() =>
      expect(screen.getByTestId("generate-button")).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId("generate-button"));

    // Optimistic decrement of 1
    expect(useCreditsStore.getState().dailyCredits).toBe(4);
  });

  // 8. Credit revert on error
  it("reverts credit on API error", async () => {
    server.use(
      http.get(QUESTIONS_URL, () => HttpResponse.json([])),
      http.post(GENERATE_URL, () =>
        HttpResponse.json({ error: "fail" }, { status: 500 }),
      ),
    );
    const user = userEvent.setup();
    useCreditsStore.setState({ dailyCredits: 5 });

    renderComponent();

    await waitFor(() =>
      expect(screen.getByTestId("generate-button")).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId("generate-button"));

    // Should revert back to original
    await waitFor(() =>
      expect(useCreditsStore.getState().dailyCredits).toBe(5),
    );
  });

  // 9. Generate button disabled when insufficient credits
  it("disables generate button when no credits remaining", async () => {
    server.use(http.get(QUESTIONS_URL, () => HttpResponse.json([])));
    useCreditsStore.setState({ dailyCredits: 0 });

    renderComponent();

    await waitFor(() =>
      expect(screen.getByTestId("generate-button")).toBeInTheDocument(),
    );

    const btn = screen.getByTestId("generate-button");
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText(/Insufficient credits/)).toBeInTheDocument();
  });
});
