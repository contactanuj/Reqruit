// StarStoryList.test.tsx — FE-11.1 list tests

import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
} from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StarStoryList } from "./StarStoryList";
import type { StarStory } from "../types";

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
// Fixtures
// ---------------------------------------------------------------------------

const stories: StarStory[] = [
  {
    id: "s-1",
    title: "Led database migration",
    situation:
      "Our legacy Postgres database was hitting performance limits under peak traffic causing customer-facing outages every week",
    task: "Plan and execute migration to sharded setup",
    action: "Coordinated across 3 engineering teams",
    result: "Zero downtime migration, 40% latency reduction",
    tags: ["leadership", "technical"],
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-02T00:00:00Z",
  },
  {
    id: "s-2",
    title: "Resolved team conflict",
    situation: "Two senior engineers disagreed on architecture",
    task: "Mediate and find consensus",
    action: "Facilitated design review sessions",
    result: "Adopted hybrid approach, shipped on time",
    tags: ["conflict resolution"],
    created_at: "2025-02-01T00:00:00Z",
    updated_at: "2025-02-02T00:00:00Z",
  },
];

// ---------------------------------------------------------------------------
// MSW Handlers
// ---------------------------------------------------------------------------

const BASE = "http://localhost:8000";

const handlers = [
  http.get(`${BASE}/interview/star-stories`, () =>
    HttpResponse.json(stories),
  ),
  http.post(`${BASE}/interview/star-stories`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      id: "s-new",
      ...body,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  }),
  http.patch(`${BASE}/interview/star-stories/:id`, async ({ request, params }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const existing = stories.find((s) => s.id === params.id);
    return HttpResponse.json({
      ...existing,
      ...body,
      updated_at: new Date().toISOString(),
    });
  }),
  http.delete(`${BASE}/interview/star-stories/:id`, () =>
    HttpResponse.json(null, { status: 200 }),
  ),
];

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
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

function renderList() {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <StarStoryList />
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("StarStoryList (FE-11.1)", () => {
  // 1. Renders loading state initially
  it("renders loading state initially", () => {
    renderList();
    expect(screen.getByTestId("loading-state")).toBeInTheDocument();
  });

  // 2. Renders stories after fetch
  it("renders stories after fetch", async () => {
    renderList();

    await waitFor(() =>
      expect(screen.getByTestId("star-story-card-s-1")).toBeInTheDocument(),
    );

    expect(screen.getByTestId("star-story-card-s-2")).toBeInTheDocument();
    expect(screen.getByText("Led database migration")).toBeInTheDocument();
    expect(screen.getByText("Resolved team conflict")).toBeInTheDocument();
  });

  // 3. Shows empty state when no stories
  it("shows empty state when no stories", async () => {
    server.use(
      http.get(`${BASE}/interview/star-stories`, () =>
        HttpResponse.json([]),
      ),
    );

    renderList();

    await waitFor(() =>
      expect(screen.getByTestId("empty-state")).toBeInTheDocument(),
    );

    expect(screen.getByText(/no star stories yet/i)).toBeInTheDocument();
  });

  // 4. Add button opens form
  it("add button opens form", async () => {
    const user = userEvent.setup();
    renderList();

    await waitFor(() =>
      expect(screen.getByTestId("add-story-button")).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId("add-story-button"));

    expect(screen.getByTestId("star-story-form")).toBeInTheDocument();
  });

  // 5. Submitting form calls POST
  it("submitting form calls POST and returns to list", async () => {
    const user = userEvent.setup();
    renderList();

    await waitFor(() =>
      expect(screen.getByTestId("add-story-button")).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId("add-story-button"));

    await user.type(screen.getByTestId("field-title"), "New story");
    await user.type(screen.getByTestId("field-situation"), "A situation");
    await user.type(screen.getByTestId("field-task"), "A task");
    await user.type(screen.getByTestId("field-action"), "An action");
    await user.type(screen.getByTestId("field-result"), "A result");

    await user.click(screen.getByTestId("submit-button"));

    // After successful creation, form should close and list should show
    await waitFor(() =>
      expect(screen.getByTestId("add-story-button")).toBeInTheDocument(),
    );
  });

  // 6. Edit button opens form with pre-filled data
  it("edit button opens form with pre-filled data", async () => {
    const user = userEvent.setup();
    renderList();

    await waitFor(() =>
      expect(screen.getByTestId("edit-story-s-1")).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId("edit-story-s-1"));

    expect(screen.getByTestId("star-story-form")).toBeInTheDocument();
    expect(screen.getByTestId("field-title")).toHaveValue(
      "Led database migration",
    );
    expect(screen.getByTestId("field-situation")).toHaveValue(
      stories[0].situation,
    );
  });

  // 7. Delete calls DELETE with confirmation
  it("delete calls DELETE with confirmation", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    renderList();

    await waitFor(() =>
      expect(screen.getByTestId("delete-story-s-1")).toBeInTheDocument(),
    );

    // Override GET so refetch after delete returns filtered list
    server.use(
      http.get(`${BASE}/interview/star-stories`, () =>
        HttpResponse.json([stories[1]]),
      ),
    );

    await user.click(screen.getByTestId("delete-story-s-1"));

    expect(confirmSpy).toHaveBeenCalledWith(
      'Delete "Led database migration"? This cannot be undone.',
    );

    // After optimistic delete + refetch, card should disappear
    await waitFor(() =>
      expect(screen.queryByTestId("star-story-card-s-1")).not.toBeInTheDocument(),
    );

    confirmSpy.mockRestore();
  });

  // 8. Accessible: story cards have proper roles
  it("story cards have proper article role", async () => {
    renderList();

    await waitFor(() =>
      expect(screen.getByTestId("star-story-card-s-1")).toBeInTheDocument(),
    );

    const cards = screen.getAllByRole("article");
    expect(cards).toHaveLength(2);

    // Edit/Delete buttons have aria-labels
    expect(screen.getByTestId("edit-story-s-1")).toHaveAttribute(
      "aria-label",
      "Edit Led database migration",
    );
    expect(screen.getByTestId("delete-story-s-1")).toHaveAttribute(
      "aria-label",
      "Delete Led database migration",
    );
  });
});
