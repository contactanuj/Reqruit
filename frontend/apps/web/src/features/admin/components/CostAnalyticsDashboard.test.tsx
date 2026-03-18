// CostAnalyticsDashboard.test.tsx — FE-15.5 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CostAnalyticsDashboard } from "./CostAnalyticsDashboard";
import type { CostAnalytics } from "../types";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

// Mock recharts to avoid SVG rendering issues in jsdom
vi.mock("recharts", () => ({
  LineChart: ({ children }: { children: React.ReactNode }) =>
    <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) =>
    <div data-testid="responsive-container">{children}</div>,
}));

const mockAnalytics: CostAnalytics = {
  totalSpend: 1234.56,
  dailyTrend: [
    { date: "2026-03-15", cost: 10.5 },
    { date: "2026-03-16", cost: 25.3 },
    { date: "2026-03-17", cost: 18.7 },
  ],
  topUsersByCost: [
    { id: "user-1", name: "Alice", totalCost: 500.0, isAnomaly: false },
    { id: "user-2", name: "Bob", totalCost: 450.0, isAnomaly: true },
  ],
  topAgentsByCost: [
    { id: "agent-1", name: "Resume Agent", totalCost: 300.0, isAnomaly: false },
    { id: "agent-2", name: "Outreach Agent", totalCost: 200.0, isAnomaly: true },
  ],
};

const server = setupServer(
  http.get("http://localhost:8000/admin/costs/analytics", () =>
    HttpResponse.json(mockAnalytics),
  ),
  http.get("http://localhost:8000/admin/costs/users/:userId", () =>
    HttpResponse.json({
      userId: "user-1",
      dailyCosts: [{ date: "2026-03-17", cost: 15.0 }],
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

function renderDashboard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <CostAnalyticsDashboard />
    </QueryClientProvider>,
  );
}

describe("CostAnalyticsDashboard (FE-15.5)", () => {
  it("renders total spend card with formatted amount", async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("cost-dashboard")).toBeInTheDocument();
    });

    expect(screen.getByTestId("total-spend")).toHaveTextContent("$1234.56");
  });

  it("renders cost trend chart container", async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("cost-trend-chart")).toBeInTheDocument();
    });

    // Mocked recharts renders a div
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
  });

  it("renders top users table", async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("top-users-table")).toBeInTheDocument();
    });

    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByTestId("cost-row-user-1")).toBeInTheDocument();
    expect(screen.getByTestId("cost-row-user-2")).toBeInTheDocument();
  });

  it("renders top agents table", async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("top-agents-table")).toBeInTheDocument();
    });

    expect(screen.getByText("Resume Agent")).toBeInTheDocument();
    expect(screen.getByText("Outreach Agent")).toBeInTheDocument();
  });

  it("shows anomaly indicator for flagged entries", async () => {
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("cost-dashboard")).toBeInTheDocument();
    });

    // Bob (user-2) is anomalous
    expect(screen.getByTestId("anomaly-indicator-user-2")).toBeInTheDocument();
    expect(screen.getByTestId("anomaly-indicator-user-2")).toHaveTextContent("Anomaly detected");

    // Alice (user-1) is not
    expect(screen.queryByTestId("anomaly-indicator-user-1")).not.toBeInTheDocument();

    // Outreach Agent (agent-2) is anomalous
    expect(screen.getByTestId("anomaly-indicator-agent-2")).toBeInTheDocument();
    expect(screen.queryByTestId("anomaly-indicator-agent-1")).not.toBeInTheDocument();
  });

  it("shows skeleton while loading", () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <CostAnalyticsDashboard />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("cost-dashboard-skeleton")).toBeInTheDocument();
  });
});
