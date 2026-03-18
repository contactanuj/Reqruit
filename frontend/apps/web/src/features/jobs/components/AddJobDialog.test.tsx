// AddJobDialog.test.tsx — FE-5.2 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AddJobDialog } from "./AddJobDialog";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const mockParsed = {
  title: "Software Engineer",
  company: "Parsed Co",
  location: "Remote",
  description: "A great job with lots of interesting challenges and requirements.",
};

const server = setupServer(
  http.post("http://localhost:8000/jobs/parse-url", () =>
    HttpResponse.json(mockParsed)
  ),
  http.post("http://localhost:8000/jobs", () =>
    HttpResponse.json({
      id: "new-job",
      title: "Software Engineer",
      company: "Parsed Co",
      location: "Remote",
      created_at: new Date().toISOString(),
      status: "saved",
    })
  ),
  http.get("http://localhost:8000/jobs", () => HttpResponse.json([]))
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

function renderComponent(props?: Partial<Parameters<typeof AddJobDialog>[0]>) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <AddJobDialog open={true} onClose={vi.fn()} {...props} />
    </QueryClientProvider>
  );
}

describe("AddJobDialog (FE-5.2)", () => {
  it("shows URL paste field by default", () => {
    renderComponent();
    expect(screen.getByLabelText(/paste job url/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /parse/i })).toBeInTheDocument();
  });

  it("URL parse success → fields auto-populated", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.type(screen.getByLabelText(/paste job url/i), "https://example.com/job/123");
    await user.click(screen.getByRole("button", { name: /parse/i }));

    await waitFor(() => {
      expect(screen.getByDisplayValue("Software Engineer")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Parsed Co")).toBeInTheDocument();
    });
  });

  it("URL parse failure → manual form shown with inline message", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("http://localhost:8000/jobs/parse-url", () =>
        HttpResponse.json({ detail: "Failed" }, { status: 422 })
      )
    );

    renderComponent();
    await user.type(screen.getByLabelText(/paste job url/i), "https://bad-url.com");
    await user.click(screen.getByRole("button", { name: /parse/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/Couldn't parse this URL/i)
      ).toBeInTheDocument();
    });
  });

  it("shows JD too short warning when description < 100 chars", async () => {
    const user = userEvent.setup();
    renderComponent();

    // Switch to manual mode
    await user.click(screen.getByText(/Enter manually/i));

    const textarea = screen.getByLabelText(/job description/i);
    await user.type(textarea, "Short JD");

    expect(
      screen.getByText(/Add more detail for better AI matching/i)
    ).toBeInTheDocument();
  });

  it("does not show JD warning when description >= 100 chars", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByText(/Enter manually/i));
    const textarea = screen.getByLabelText(/job description/i);
    await user.type(
      textarea,
      "This is a long enough job description that has more than one hundred characters in total so it passes."
    );

    expect(
      screen.queryByText(/Add more detail for better AI matching/i)
    ).not.toBeInTheDocument();
  });

  it("saves job and shows success toast on submit", async () => {
    const { toast } = await import("sonner");
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderComponent({ onClose });

    await user.click(screen.getByText(/Enter manually/i));
    await user.type(screen.getByLabelText(/job title/i), "Software Engineer");
    await user.type(screen.getByLabelText(/company/i), "Test Co");

    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Job saved", expect.any(Object));
    });
  });
});
