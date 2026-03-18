// DiscoveryHealthTable.test.tsx — FE-15.2 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DiscoveryHealthTable } from "./DiscoveryHealthTable";
import type { DiscoverySource } from "../types";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const mockSources: DiscoverySource[] = [
  { id: "src-1", name: "LinkedIn", lastSyncTime: "2026-03-17T10:00:00Z", status: "healthy" },
  { id: "src-2", name: "Indeed", lastSyncTime: "2026-03-17T08:00:00Z", status: "degraded" },
  { id: "src-3", name: "Glassdoor", lastSyncTime: "2026-03-16T12:00:00Z", status: "failed" },
];

const server = setupServer(
  http.get("http://localhost:8000/admin/discovery/sources", () =>
    HttpResponse.json(mockSources),
  ),
  http.post("http://localhost:8000/admin/discovery/sources/:id/sync", () =>
    HttpResponse.json(null, { status: 200 }),
  ),
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
      <DiscoveryHealthTable />
    </QueryClientProvider>,
  );
}

describe("DiscoveryHealthTable (FE-15.2)", () => {
  it("renders source rows with correct status badges", async () => {
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("discovery-health-table")).toBeInTheDocument();
    });

    expect(screen.getByTestId("source-row-src-1")).toBeInTheDocument();
    expect(screen.getByTestId("source-row-src-2")).toBeInTheDocument();
    expect(screen.getByTestId("source-row-src-3")).toBeInTheDocument();

    // Status badge text
    expect(screen.getByTestId("status-badge-src-1")).toHaveTextContent("Healthy");
    expect(screen.getByTestId("status-badge-src-2")).toHaveTextContent("Degraded");
    expect(screen.getByTestId("status-badge-src-3")).toHaveTextContent("Failed");
  });

  it("status badges have correct color classes", async () => {
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("status-badge-src-1")).toBeInTheDocument();
    });

    expect(screen.getByTestId("status-badge-src-1").className).toContain("bg-green-100");
    expect(screen.getByTestId("status-badge-src-2").className).toContain("bg-yellow-100");
    expect(screen.getByTestId("status-badge-src-3").className).toContain("bg-red-100");
  });

  it("sync button triggers sync and shows loading state", async () => {
    // Use a delayed response to observe loading state
    let resolveSync: (() => void) | undefined;
    server.use(
      http.post("http://localhost:8000/admin/discovery/sources/:id/sync", () => {
        return new Promise<Response>((resolve) => {
          resolveSync = () => resolve(HttpResponse.json(null, { status: 200 }) as Response);
        });
      }),
    );

    const user = userEvent.setup();
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("sync-button-src-1")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("sync-button-src-1"));

    // Should show loading text
    expect(screen.getByTestId("sync-button-src-1")).toHaveTextContent("Syncing...");
    expect(screen.getByTestId("sync-button-src-1")).toBeDisabled();

    // Resolve the sync
    resolveSync?.();

    await waitFor(() => {
      expect(screen.getByTestId("sync-button-src-1")).toHaveTextContent("Sync now");
    });
  });

  it("shows skeleton while loading", () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <DiscoveryHealthTable />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("discovery-health-skeleton")).toBeInTheDocument();
  });
});
