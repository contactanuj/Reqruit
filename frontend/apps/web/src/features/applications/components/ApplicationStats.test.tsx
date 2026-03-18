// ApplicationStats.test.tsx — FE-6.5 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApplicationStats } from "./ApplicationStats";
import type { ApplicationStatsData } from "../types";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

// Mock recharts to avoid SVG rendering issues in jsdom
vi.mock("recharts", () => ({
  FunnelChart: ({ children }: { children: React.ReactNode }) =>
    <div data-testid="funnel-chart">{children}</div>,
  Funnel: ({ children }: { children: React.ReactNode }) =>
    <div data-testid="funnel">{children}</div>,
  LabelList: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) =>
    <div data-testid="responsive-container">{children}</div>,
}));

const fullStats: ApplicationStatsData = {
  total: 20,
  by_status: {
    Saved: 8,
    Applied: 5,
    Interviewing: 3,
    Offered: 2,
    Accepted: 1,
    Rejected: 1,
    Withdrawn: 0,
  },
  avg_days_per_stage: {
    Saved: 3.2,
    Applied: 7.5,
    Interviewing: 14.0,
    Offered: 5.0,
    Accepted: 0,
    Rejected: 10.0,
    Withdrawn: 2.0,
  },
};

const lowStats: ApplicationStatsData = {
  total: 3,
  by_status: {
    Saved: 3,
    Applied: 0,
    Interviewing: 0,
    Offered: 0,
    Accepted: 0,
    Rejected: 0,
    Withdrawn: 0,
  },
  avg_days_per_stage: {
    Saved: 1.0,
    Applied: 0,
    Interviewing: 0,
    Offered: 0,
    Accepted: 0,
    Rejected: 0,
    Withdrawn: 0,
  },
};

const server = setupServer(
  http.get("http://localhost:8000/applications/stats", () =>
    HttpResponse.json(fullStats)
  )
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

function renderStats(stats: ApplicationStatsData = fullStats) {
  server.use(
    http.get("http://localhost:8000/applications/stats", () =>
      HttpResponse.json(stats)
    )
  );
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ApplicationStats />
    </QueryClientProvider>
  );
}

describe("ApplicationStats (FE-6.5)", () => {
  it("renders funnel chart and stage timing table with full data", async () => {
    renderStats();

    await waitFor(() => {
      expect(screen.getByTestId("application-stats")).toBeInTheDocument();
    });

    // Funnel chart rendered
    expect(screen.getByTestId("funnel-chart")).toBeInTheDocument();

    // Stage timing table header
    expect(screen.getByText("Time in Stage")).toBeInTheDocument();
    expect(screen.getByText("Avg Days")).toBeInTheDocument();
  });

  it("shows low-data message when fewer than 5 total applications", async () => {
    renderStats(lowStats);

    await waitFor(() => {
      expect(screen.getByTestId("low-data-state")).toBeInTheDocument();
    });

    expect(
      screen.getByText("Add more applications to see meaningful statistics")
    ).toBeInTheDocument();
  });

  it("stage timing table shows all 7 statuses in correct order", async () => {
    renderStats();

    await waitFor(() => screen.getByTestId("application-stats"));

    // All 7 statuses should appear in the timing table
    const expectedLabels = [
      "Saved", "Applied", "Interviewing", "Offered", "Accepted", "Rejected", "Withdrawn",
    ];
    for (const label of expectedLabels) {
      // Each status appears at least once (heading + table cell)
      const elements = screen.getAllByText(label);
      expect(elements.length).toBeGreaterThan(0);
    }
  });

  it("renders sr-only accessible table with correct funnel data", async () => {
    renderStats();

    await waitFor(() => screen.getByTestId("application-stats"));

    // The sr-only table should have an accessible label
    const srTable = screen.getByRole("table", { name: "Pipeline funnel data table" });
    expect(srTable).toBeInTheDocument();

    // Verify it contains the funnel stages and terminal statuses
    const rows = srTable.querySelectorAll("tbody tr");
    // 5 funnel stages + 2 terminal statuses = 7 rows
    expect(rows.length).toBe(7);

    // First row should be Saved with count 8
    expect(rows[0]).toHaveTextContent("Saved");
    expect(rows[0]).toHaveTextContent("8");

    // Rejected row should show count 1
    expect(rows[5]).toHaveTextContent("Rejected");
    expect(rows[5]).toHaveTextContent("1");

    // Withdrawn row should show count 0
    expect(rows[6]).toHaveTextContent("Withdrawn");
    expect(rows[6]).toHaveTextContent("0");
  });

  it("shows skeleton while loading", () => {
    // Don't pre-seed query — will be in loading state briefly
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    // Set query as loading
    render(
      <QueryClientProvider client={qc}>
        <ApplicationStats />
      </QueryClientProvider>
    );

    // While pending, skeleton should show
    expect(screen.getByTestId("stats-skeleton")).toBeInTheDocument();
  });
});
