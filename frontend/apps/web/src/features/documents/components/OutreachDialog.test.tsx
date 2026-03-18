// OutreachDialog.test.tsx — FE-10.1 co-located tests

import { describe, it, expect, vi, beforeEach, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { OutreachDialog } from "./OutreachDialog";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { useStreamStore } from "@/features/applications/store/stream-store";
import type { Contact } from "@/features/jobs/types";

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

vi.mock("@repo/ui/hooks/use-sse-stream", () => ({
  useSSEStream: vi.fn(),
}));

vi.mock("@repo/ui/components/StreamingText", () => ({
  StreamingText: (props: { text: string; isStreaming: boolean }) =>
    `[StreamingText text="${props.text}" streaming=${props.isStreaming}]`,
}));

vi.mock("./AgentPipelineVisualizer", () => ({
  AgentPipelineVisualizer: (props: { threadId: string }) =>
    `[PipelineVisualizer thread="${props.threadId}"]`,
}));

// ---------------------------------------------------------------------------
// MSW Handlers
// ---------------------------------------------------------------------------

const GENERATE_URL = "http://localhost:8000/jobs/:jobId/contacts/:contactId/outreach/generate";
const APPROVE_URL = "http://localhost:8000/jobs/:jobId/contacts/:contactId/outreach/approve";

const server = setupServer(
  http.post(GENERATE_URL, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ thread_id: `thread-outreach-${body.type}` });
  }),
  http.post(APPROVE_URL, () =>
    HttpResponse.json({ id: "outreach-1", is_approved: true }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
  useCreditsStore.setState({ dailyCredits: 5 });
  useStreamStore.getState().reset();
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mockContact: Contact = {
  id: "contact-1",
  name: "Jane Doe",
  role_type: "Recruiter",
  linkedin_url: "https://linkedin.com/in/janedoe",
  email: "jane@acme.com",
};

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderDialog(props: { open?: boolean; onClose?: () => void } = {}) {
  const qc = makeQueryClient();
  const onClose = props.onClose ?? vi.fn();
  return { ...render(
    <QueryClientProvider client={qc}>
      <OutreachDialog
        jobId="job-1"
        contact={mockContact}
        open={props.open ?? true}
        onClose={onClose}
      />
    </QueryClientProvider>,
  ), onClose };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("OutreachDialog (FE-10.1)", () => {
  beforeEach(() => {
    useCreditsStore.setState({ dailyCredits: 5 });
  });

  // AC #1: Dialog opens with type and tone selectors
  it("renders dialog with type and tone selectors", () => {
    renderDialog();
    expect(screen.getByTestId("outreach-dialog")).toBeInTheDocument();
    expect(screen.getByTestId("type-selector")).toBeInTheDocument();
    expect(screen.getByTestId("tone-selector")).toBeInTheDocument();
    expect(screen.getByText("LinkedIn message")).toBeInTheDocument();
    expect(screen.getByText("Email message")).toBeInTheDocument();
    expect(screen.getByText("Professional")).toBeInTheDocument();
    expect(screen.getByText("Casual")).toBeInTheDocument();
  });

  // AC #1: Contact name and role shown in header
  it("displays contact name and role in confirmation area", () => {
    renderDialog();
    expect(screen.getByTestId("contact-name")).toHaveTextContent("Jane Doe");
    expect(screen.getByTestId("contact-name")).toHaveTextContent("(Recruiter)");
  });

  // AC #1: Selecting LinkedIn vs Email sets correct payload
  it("selecting Email changes the radio selection", async () => {
    const user = userEvent.setup();
    renderDialog();
    const emailRadio = screen.getByDisplayValue("email");
    await user.click(emailRadio);
    expect(emailRadio).toBeChecked();
    expect(screen.getByDisplayValue("linkedin")).not.toBeChecked();
  });

  it("selecting Casual tone changes the radio selection", async () => {
    const user = userEvent.setup();
    renderDialog();
    const casualRadio = screen.getByDisplayValue("casual");
    await user.click(casualRadio);
    expect(casualRadio).toBeChecked();
    expect(screen.getByDisplayValue("professional")).not.toBeChecked();
  });

  // AC #2: Generate click → credit decrement + API call + SSE stream starts
  it("generate click decrements credits and calls API, stores thread_id", async () => {
    const user = userEvent.setup();
    renderDialog();

    const initialCredits = useCreditsStore.getState().dailyCredits;
    await user.click(screen.getByTestId("generate-button"));

    // Optimistic decrement
    expect(useCreditsStore.getState().dailyCredits).toBe(initialCredits - 1);

    // Thread ID stored after success
    await waitFor(() =>
      expect(useStreamStore.getState().activeThreadId).toBe("thread-outreach-linkedin"),
    );
  });

  // AC #3: HITL panel renders with contact context in right pane
  it("transitions to review phase when HITL draft is ready", async () => {
    const user = userEvent.setup();
    renderDialog();

    // Start generation
    await user.click(screen.getByTestId("generate-button"));

    // Wait for thread to be set
    await waitFor(() =>
      expect(useStreamStore.getState().activeThreadId).toBeTruthy(),
    );

    // Simulate HITL draft ready (as if SSE sent hitl_ready event)
    useStreamStore.getState().setHITL({
      content: "Hello Jane, I noticed your role at Acme...",
      threadId: "thread-outreach-linkedin",
      generationType: "outreach",
    });

    await waitFor(() =>
      expect(screen.getByTestId("review-phase")).toBeInTheDocument(),
    );

    // Contact context visible in source panel
    expect(screen.getByTestId("source-panel")).toBeInTheDocument();
    const sourcePanel = screen.getByTestId("source-panel");
    expect(within(sourcePanel).getByText(/Jane Doe/)).toBeInTheDocument();
  });

  // AC #4: Approve → API call + "Copy to clipboard" button appears
  it("approve transitions to approved phase with copy button", async () => {
    const user = userEvent.setup();
    renderDialog();

    // Fast-forward to review phase
    await user.click(screen.getByTestId("generate-button"));
    await waitFor(() =>
      expect(useStreamStore.getState().activeThreadId).toBeTruthy(),
    );
    useStreamStore.getState().setHITL({
      content: "Hello Jane, great to connect...",
      threadId: "thread-outreach-linkedin",
      generationType: "outreach",
    });
    await waitFor(() =>
      expect(screen.getByTestId("review-phase")).toBeInTheDocument(),
    );

    // Click approve
    await user.click(screen.getByTestId("approve-button"));

    await waitFor(() =>
      expect(screen.getByTestId("approved-phase")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("copy-to-clipboard-button")).toBeInTheDocument();
    expect(screen.getByTestId("copy-to-clipboard-button")).toHaveTextContent("Copy to clipboard");
  });

  // Error → credit revert + toast
  it("reverts credit on API error", async () => {
    server.use(
      http.post(GENERATE_URL, () =>
        HttpResponse.json({ error: "server error" }, { status: 500 }),
      ),
    );
    const user = userEvent.setup();
    renderDialog();
    const initialCredits = useCreditsStore.getState().dailyCredits;

    await user.click(screen.getByTestId("generate-button"));

    await waitFor(() =>
      expect(useCreditsStore.getState().dailyCredits).toBe(initialCredits),
    );
  });

  // Keyboard: Escape closes
  it("Escape key closes dialog via useFocusTrap", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderDialog({ onClose });

    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  // Disabled generate when no credits
  it("generate button disabled when 0 credits", () => {
    useCreditsStore.setState({ dailyCredits: 0 });
    renderDialog();
    expect(screen.getByTestId("generate-button")).toBeDisabled();
  });

  // Does not render when closed
  it("does not render when open is false", () => {
    renderDialog({ open: false });
    expect(screen.queryByTestId("outreach-dialog")).not.toBeInTheDocument();
  });
});
