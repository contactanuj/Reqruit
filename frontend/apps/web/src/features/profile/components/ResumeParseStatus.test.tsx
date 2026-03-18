// ResumeParseStatus.test.tsx — FE-4.2 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResumeParseStatus } from "./ResumeParseStatus";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/profile",
}));

// Mock sonner
const mockToastSuccess = vi.fn();
vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => mockToastSuccess(...args),
    error: vi.fn(),
  },
}));

// ---------------------------------------------------------------------------
// MSW server
// ---------------------------------------------------------------------------

let statusResponse = { id: "resume-123", status: "processing", message: null };

const handlers = [
  http.get("http://localhost:8000/resumes/:id/status", ({ params }) => {
    return HttpResponse.json({ ...statusResponse, id: params.id });
  }),
];

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
  statusResponse = { id: "resume-123", status: "processing", message: null };
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderComponent(resumeId = "resume-123", onComplete?: () => void, onRetry?: () => void) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <ResumeParseStatus resumeId={resumeId} onComplete={onComplete} onRetry={onRetry} />
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ResumeParseStatus (FE-4.2)", () => {
  it("shows processing step indicator while status is processing", async () => {
    renderComponent();

    await waitFor(() => {
      // Use aria-current="step" to find the active step
      const activeStep = document.querySelector('[aria-current="step"]');
      expect(activeStep).toBeInTheDocument();
      // The active step should be the Processing step
      expect(activeStep?.nextElementSibling?.textContent).toMatch(/processing/i);
    });
  });

  it("shows success state and calls onComplete when status is completed", async () => {
    statusResponse = { id: "resume-123", status: "completed", message: null };
    const onComplete = vi.fn();
    renderComponent("resume-123", onComplete);

    await waitFor(() => {
      expect(screen.getByText(/parsed successfully/i)).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalled();
    });
  });

  it("shows error state with retry CTA when status is failed", async () => {
    statusResponse = { id: "resume-123", status: "failed", message: null };
    const onRetry = vi.fn();
    renderComponent("resume-123", undefined, onRetry);

    await waitFor(() => {
      expect(screen.getByText(/couldn't parse/i)).toBeInTheDocument();
    });

    const retryBtn = screen.getByRole("button", { name: /try again/i });
    expect(retryBtn).toBeInTheDocument();

    await userEvent.click(retryBtn);
    expect(onRetry).toHaveBeenCalled();
  });

  it("shows toast success when parsing completes", async () => {
    statusResponse = { id: "resume-123", status: "completed", message: null };
    renderComponent("resume-123");

    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalledWith(
        "Resume parsed successfully",
        expect.any(Object)
      );
    });
  });
});
