// GenerateButton.test.tsx — FE-7.1 tests

import { describe, it, expect, vi, beforeEach, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { GenerateButton } from "./GenerateButton";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { useStreamStore } from "@/features/applications/store/stream-store";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const server = setupServer(
  http.post("http://localhost:8000/applications/:id/cover-letter/generate", () =>
    HttpResponse.json({ thread_id: "thread-abc-123" })
  )
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
  // Reset stores
  useCreditsStore.setState({ dailyCredits: 5 });
  useStreamStore.getState().reset();
});

function makeQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
}

function renderButton(props: { applicationId?: string; hasMasterResume?: boolean; onGenerated?: () => void } = {}) {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <GenerateButton
        applicationId={props.applicationId ?? "app-1"}
        hasMasterResume={props.hasMasterResume ?? true}
        onGenerated={props.onGenerated}
      />
    </QueryClientProvider>
  );
}

describe("GenerateButton (FE-7.1)", () => {
  beforeEach(() => {
    useCreditsStore.setState({ dailyCredits: 5 });
  });

  it("renders enabled button when master resume exists and credits > 0", () => {
    renderButton({ hasMasterResume: true });
    const btn = screen.getByTestId("generate-button");
    expect(btn).toBeInTheDocument();
    expect(btn).not.toBeDisabled();
    expect(btn).toHaveTextContent("Generate Cover Letter");
  });

  it("renders disabled button with tooltip when no master resume", () => {
    renderButton({ hasMasterResume: false });
    const btn = screen.getByTestId("generate-button");
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-disabled", "true");
    // Tooltip text
    expect(screen.getByRole("tooltip")).toHaveTextContent(
      "Upload and set a master resume first"
    );
  });

  it("renders disabled button with upgrade CTA when 0 credits", () => {
    useCreditsStore.setState({ dailyCredits: 0 });
    renderButton({ hasMasterResume: true });
    const btn = screen.getByTestId("generate-button");
    expect(btn).toBeDisabled();
    expect(screen.getByTestId("no-credits-message")).toHaveTextContent(
      "0 credits remaining"
    );
    expect(screen.getByRole("link", { name: /upgrade for more/i })).toBeInTheDocument();
  });

  it("shows low credits warning when exactly 1 credit remains", () => {
    useCreditsStore.setState({ dailyCredits: 1 });
    renderButton({ hasMasterResume: true });
    expect(screen.getByTestId("low-credits-warning")).toHaveTextContent(
      "1 credit remaining"
    );
  });

  it("click decrements credits and calls POST /cover-letter/generate", async () => {
    const user = userEvent.setup();
    const onGenerated = vi.fn();
    renderButton({ hasMasterResume: true, onGenerated });

    const initialCredits = useCreditsStore.getState().dailyCredits;
    await user.click(screen.getByTestId("generate-button"));

    // Optimistic decrement
    expect(useCreditsStore.getState().dailyCredits).toBe(initialCredits - 1);

    // onGenerated called after success
    await waitFor(() => expect(onGenerated).toHaveBeenCalledOnce());

    // thread_id stored in stream store
    expect(useStreamStore.getState().activeThreadId).toBe("thread-abc-123");
  });

  it("reverts credit on API error", async () => {
    server.use(
      http.post("http://localhost:8000/applications/:id/cover-letter/generate", () =>
        HttpResponse.json({ error: "server error" }, { status: 500 })
      )
    );
    const user = userEvent.setup();
    renderButton({ hasMasterResume: true });
    const initialCredits = useCreditsStore.getState().dailyCredits;

    await user.click(screen.getByTestId("generate-button"));

    await waitFor(() =>
      expect(useCreditsStore.getState().dailyCredits).toBe(initialCredits)
    );
  });
});
