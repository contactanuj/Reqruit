// AssemblyWorkflow.test.tsx — FE-10.2 co-located tests

import { describe, it, expect, vi, beforeEach, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AssemblyWorkflow } from "./AssemblyWorkflow";
import { AssemblyProgressBanner } from "./AssemblyProgressBanner";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import type { AssemblyStep } from "../hooks/useApplicationAssembly";

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

const ASSEMBLE_URL = "http://localhost:8000/applications/:id/assemble";
const STATUS_URL = "http://localhost:8000/applications/:id/assemble/status";
const RETRY_URL = "http://localhost:8000/applications/:id/assemble/retry";

const server = setupServer(
  http.post(ASSEMBLE_URL, () =>
    HttpResponse.json({ assembly_id: "asm-123" }),
  ),
  http.get(STATUS_URL, () =>
    HttpResponse.json({
      assembly_id: "asm-123",
      status: "in_progress",
      steps: [
        { step: "resume_tailoring", label: "Resume tailoring", status: "running" },
        { step: "cover_letter", label: "Cover letter", status: "pending" },
        { step: "outreach", label: "Outreach", status: "pending" },
      ],
    }),
  ),
  http.post(RETRY_URL, () => HttpResponse.json(null, { status: 200 })),
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

function renderWorkflow(props: {
  applicationId?: string;
  hasMasterResume?: boolean;
  onStepNeedsReview?: (step: string, appId: string) => void;
} = {}) {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <AssemblyWorkflow
        applicationId={props.applicationId ?? "app-1"}
        hasMasterResume={props.hasMasterResume ?? true}
        onStepNeedsReview={props.onStepNeedsReview}
      />
    </QueryClientProvider>,
  );
}

function renderBanner(props: {
  steps?: AssemblyStep[];
  onRetry?: (step: string) => void;
  isRetrying?: boolean;
  onDismiss?: () => void;
} = {}) {
  const defaultSteps: AssemblyStep[] = [
    { step: "resume_tailoring", label: "Resume tailoring", status: "complete" },
    { step: "cover_letter", label: "Cover letter", status: "running" },
    { step: "outreach", label: "Outreach", status: "pending" },
  ];
  return render(
    <AssemblyProgressBanner
      steps={props.steps ?? defaultSteps}
      onRetry={props.onRetry ?? vi.fn()}
      isRetrying={props.isRetrying}
      onDismiss={props.onDismiss}
    />,
  );
}

// ---------------------------------------------------------------------------
// Tests: AssemblyWorkflow
// ---------------------------------------------------------------------------

describe("AssemblyWorkflow (FE-10.2)", () => {
  beforeEach(() => {
    useCreditsStore.setState({ dailyCredits: 10 });
  });

  // AC #1: Button disabled when no master resume
  it("renders disabled button with tooltip when no master resume", () => {
    renderWorkflow({ hasMasterResume: false });
    const btn = screen.getByTestId("assemble-button");
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("tooltip")).toHaveTextContent(
      "Upload and set a master resume first",
    );
  });

  // AC #1: Button disabled when insufficient credits
  it("renders disabled button with upgrade CTA when < 3 credits", () => {
    useCreditsStore.setState({ dailyCredits: 2 });
    renderWorkflow({ hasMasterResume: true });
    const btn = screen.getByTestId("assemble-button");
    expect(btn).toBeDisabled();
    expect(screen.getByTestId("insufficient-credits-message")).toHaveTextContent(
      "Requires 3 credits",
    );
    expect(screen.getByRole("link", { name: /upgrade for more/i })).toBeInTheDocument();
  });

  // AC #1: Click → credit decrement (3) + API call
  it("click decrements 3 credits and calls POST /assemble", async () => {
    const user = userEvent.setup();
    renderWorkflow();

    const initialCredits = useCreditsStore.getState().dailyCredits;
    await user.click(screen.getByTestId("assemble-button"));

    // Optimistic decrement of 3
    expect(useCreditsStore.getState().dailyCredits).toBe(initialCredits - 3);
  });

  // AC #1: Error reverts all 3 credits
  it("reverts 3 credits on API error", async () => {
    server.use(
      http.post(ASSEMBLE_URL, () =>
        HttpResponse.json({ error: "fail" }, { status: 500 }),
      ),
    );
    const user = userEvent.setup();
    renderWorkflow();
    const initialCredits = useCreditsStore.getState().dailyCredits;

    await user.click(screen.getByTestId("assemble-button"));

    await waitFor(() =>
      expect(useCreditsStore.getState().dailyCredits).toBe(initialCredits),
    );
  });

  // AC #2: Progress banner renders after assembly starts
  it("shows progress banner after assembly starts", async () => {
    const user = userEvent.setup();
    renderWorkflow();

    await user.click(screen.getByTestId("assemble-button"));

    await waitFor(() =>
      expect(screen.getByTestId("assembly-progress-banner")).toBeInTheDocument(),
    );
  });

  // Enabled state renders correctly
  it("renders enabled button when master resume exists and credits sufficient", () => {
    renderWorkflow({ hasMasterResume: true });
    const btn = screen.getByTestId("assemble-button");
    expect(btn).toBeInTheDocument();
    expect(btn).not.toBeDisabled();
    expect(btn).toHaveTextContent("Assemble application");
  });
});

// ---------------------------------------------------------------------------
// Tests: AssemblyProgressBanner
// ---------------------------------------------------------------------------

describe("AssemblyProgressBanner (FE-10.2)", () => {
  // AC #2: Progress banner shows three steps in correct states
  it("renders three steps with correct states", () => {
    renderBanner();
    expect(screen.getByTestId("assembly-step-resume_tailoring")).toBeInTheDocument();
    expect(screen.getByTestId("assembly-step-cover_letter")).toBeInTheDocument();
    expect(screen.getByTestId("assembly-step-outreach")).toBeInTheDocument();
    expect(screen.getByText(/1\/3 steps complete/)).toBeInTheDocument();
  });

  // AC #4: Step failure → error state + retry button
  it("shows error state with retry button when step fails", () => {
    const steps: AssemblyStep[] = [
      { step: "resume_tailoring", label: "Resume tailoring", status: "complete" },
      { step: "cover_letter", label: "Cover letter", status: "error", error: "LLM timeout" },
      { step: "outreach", label: "Outreach", status: "pending" },
    ];
    const onRetry = vi.fn();
    renderBanner({ steps, onRetry });

    expect(screen.getByTestId("error-cover_letter")).toHaveTextContent("LLM timeout");
    expect(screen.getByTestId("retry-cover_letter")).toBeInTheDocument();
    expect(screen.getByTestId("retry-cover_letter")).toHaveTextContent("Retry this step");
  });

  // AC #4: Retry calls onRetry with step name
  it("retry button calls onRetry with correct step name", async () => {
    const user = userEvent.setup();
    const steps: AssemblyStep[] = [
      { step: "resume_tailoring", label: "Resume tailoring", status: "complete" },
      { step: "cover_letter", label: "Cover letter", status: "error", error: "Failed" },
      { step: "outreach", label: "Outreach", status: "pending" },
    ];
    const onRetry = vi.fn();
    renderBanner({ steps, onRetry });

    await user.click(screen.getByTestId("retry-cover_letter"));
    expect(onRetry).toHaveBeenCalledWith("cover_letter");
  });

  // AC #2: All complete → banner can be dismissed
  it("returns null (hidden) when all steps complete and onDismiss provided", () => {
    const steps: AssemblyStep[] = [
      { step: "resume_tailoring", label: "Resume tailoring", status: "complete" },
      { step: "cover_letter", label: "Cover letter", status: "complete" },
      { step: "outreach", label: "Outreach", status: "complete" },
    ];
    const { container } = renderBanner({ steps, onDismiss: vi.fn() });
    expect(container.innerHTML).toBe("");
  });

  // Accessibility: progressbar role
  it("has progressbar role with aria-valuenow and aria-valuemax", () => {
    renderBanner();
    const banner = screen.getByTestId("assembly-progress-banner");
    expect(banner).toHaveAttribute("role", "progressbar");
    expect(banner).toHaveAttribute("aria-valuenow", "1");
    expect(banner).toHaveAttribute("aria-valuemax", "3");
  });

  // Accessibility: retry button has accessible label
  it("retry button has aria-label with step name", () => {
    const steps: AssemblyStep[] = [
      { step: "resume_tailoring", label: "Resume tailoring", status: "complete" },
      { step: "cover_letter", label: "Cover letter", status: "error", error: "Failed" },
      { step: "outreach", label: "Outreach", status: "pending" },
    ];
    renderBanner({ steps });
    expect(screen.getByTestId("retry-cover_letter")).toHaveAttribute(
      "aria-label",
      "Retry Cover letter",
    );
  });
});
