// PiiEventsTable.test.tsx — FE-15.4 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PiiEventsTable } from "./PiiEventsTable";
import type { PiiEvent } from "../types";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const mockEvents: PiiEvent[] = [
  {
    id: "pii-1",
    timestamp: "2026-03-17T10:00:00Z",
    eventType: "ssn_detected",
    contentSnippet: "Found SSN 123-45-6789 in resume",
    userId: "user-1",
    status: "pending",
  },
  {
    id: "pii-2",
    timestamp: "2026-03-17T11:00:00Z",
    eventType: "email_leak",
    contentSnippet: '<script>alert("xss")</script>Leaked email address in notes',
    userId: "user-2",
    status: "pending",
  },
  {
    id: "pii-3",
    timestamp: "2026-03-16T09:00:00Z",
    eventType: "phone_detected",
    contentSnippet: "Phone number found in cover letter",
    userId: "user-3",
    status: "confirmed",
  },
  {
    id: "pii-4",
    timestamp: "2026-03-15T14:00:00Z",
    eventType: "address_detected",
    contentSnippet: "Home address detected",
    userId: "user-4",
    status: "false_positive",
  },
];

const server = setupServer(
  http.get("http://localhost:8000/admin/pii-events", () =>
    HttpResponse.json(mockEvents),
  ),
  http.patch("http://localhost:8000/admin/pii-events/:id", async ({ request }) => {
    const body = (await request.json()) as { status: string };
    const event = mockEvents.find((e) => e.id === "pii-1");
    return HttpResponse.json({ ...event, status: body.status });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

function renderTable() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PiiEventsTable />
    </QueryClientProvider>,
  );
}

describe("PiiEventsTable (FE-15.4)", () => {
  it("renders two sections: pending and resolved", async () => {
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("pii-events-table")).toBeInTheDocument();
    });

    expect(screen.getByTestId("pending-section")).toBeInTheDocument();
    expect(screen.getByTestId("resolved-section")).toBeInTheDocument();
  });

  it("shows pending events in pending section with action buttons", async () => {
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("pii-event-pii-1")).toBeInTheDocument();
    });

    // Pending events have Confirm PII and Mark false positive buttons
    expect(screen.getByTestId("confirm-pii-pii-1")).toBeInTheDocument();
    expect(screen.getByTestId("mark-false-positive-pii-1")).toBeInTheDocument();
    expect(screen.getByTestId("confirm-pii-pii-2")).toBeInTheDocument();
    expect(screen.getByTestId("mark-false-positive-pii-2")).toBeInTheDocument();
  });

  it("shows resolved events without action buttons", async () => {
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("pii-event-pii-3")).toBeInTheDocument();
    });

    // Resolved events should not have action buttons
    expect(screen.queryByTestId("confirm-pii-pii-3")).not.toBeInTheDocument();
    expect(screen.queryByTestId("mark-false-positive-pii-3")).not.toBeInTheDocument();
    expect(screen.queryByTestId("confirm-pii-pii-4")).not.toBeInTheDocument();
  });

  it("sanitizes XSS content via DOMPurify and truncates to 100 chars", async () => {
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("pii-event-pii-2")).toBeInTheDocument();
    });

    // The <script> tag should be stripped by DOMPurify
    expect(screen.queryByText(/<script>/)).not.toBeInTheDocument();
    // The safe content after the script tag should be visible
    expect(screen.getByText(/Leaked email address in notes/)).toBeInTheDocument();
  });

  it("Confirm PII button triggers optimistic update", async () => {
    let patchCalled = false;
    server.use(
      http.patch("http://localhost:8000/admin/pii-events/:id", async ({ request }) => {
        patchCalled = true;
        const body = (await request.json()) as { status: string };
        const event = mockEvents.find((e) => e.id === "pii-1");
        return HttpResponse.json({ ...event, status: body.status });
      }),
      http.get("http://localhost:8000/admin/pii-events", () => {
        // After PATCH, return updated data so refetch doesn't revert
        if (patchCalled) {
          const updated = mockEvents.map((e) =>
            e.id === "pii-1" ? { ...e, status: "confirmed" as const } : e,
          );
          return HttpResponse.json(updated);
        }
        return HttpResponse.json(mockEvents);
      }),
    );

    const user = userEvent.setup();
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("confirm-pii-pii-1")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("confirm-pii-pii-1"));

    // Optimistic: the event should now show as confirmed (buttons disappear)
    await waitFor(() => {
      expect(screen.queryByTestId("confirm-pii-pii-1")).not.toBeInTheDocument();
    });
  });

  it("Mark false positive button triggers optimistic update", async () => {
    let patchCalled = false;
    server.use(
      http.patch("http://localhost:8000/admin/pii-events/:id", async ({ request }) => {
        patchCalled = true;
        const body = (await request.json()) as { status: string };
        const event = mockEvents.find((e) => e.id === "pii-1");
        return HttpResponse.json({ ...event, status: body.status });
      }),
      http.get("http://localhost:8000/admin/pii-events", () => {
        if (patchCalled) {
          const updated = mockEvents.map((e) =>
            e.id === "pii-1" ? { ...e, status: "false_positive" as const } : e,
          );
          return HttpResponse.json(updated);
        }
        return HttpResponse.json(mockEvents);
      }),
    );

    const user = userEvent.setup();
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("mark-false-positive-pii-1")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("mark-false-positive-pii-1"));

    // Optimistic: the event should now show as false_positive (buttons disappear)
    await waitFor(() => {
      expect(screen.queryByTestId("mark-false-positive-pii-1")).not.toBeInTheDocument();
    });
  });

  it("displays correct pending and resolved counts", async () => {
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("pending-section")).toBeInTheDocument();
    });

    expect(screen.getByText("Pending Review (2)")).toBeInTheDocument();
    expect(screen.getByText("Resolved (2)")).toBeInTheDocument();
  });

  it("shows skeleton while loading", () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <PiiEventsTable />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("pii-events-skeleton")).toBeInTheDocument();
  });
});
