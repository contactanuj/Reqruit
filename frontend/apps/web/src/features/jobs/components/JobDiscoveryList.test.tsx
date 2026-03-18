// JobDiscoveryList.test.tsx — FE-5.1 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { JobDiscoveryList } from "./JobDiscoveryList";
import type { SavedJob } from "../types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/jobs",
}));

const mockJobs: SavedJob[] = [
  {
    id: "1",
    title: "Frontend Engineer",
    company: "Alpha Inc",
    location: "Remote",
    fit_score: 90,
    roi_prediction: "High ROI",
    created_at: "2026-03-01T00:00:00Z",
    status: "saved",
  },
  {
    id: "2",
    title: "Backend Engineer",
    company: "Beta Ltd",
    location: "London",
    fit_score: 75,
    created_at: "2026-03-02T00:00:00Z",
    status: "saved",
  },
  {
    id: "3",
    title: "Full Stack Dev",
    company: "Gamma Co",
    location: "Berlin",
    fit_score: 80,
    created_at: "2026-03-03T00:00:00Z",
    status: "saved",
  },
];

let jobsData: SavedJob[] | null = mockJobs;

const server = setupServer(
  http.get("http://localhost:8000/jobs/shortlist", () => {
    if (jobsData === null) {
      return HttpResponse.json([]);
    }
    return HttpResponse.json(jobsData);
  })
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
  jobsData = mockJobs;
});

function renderComponent() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <JobDiscoveryList locale="US" />
    </QueryClientProvider>
  );
}

describe("JobDiscoveryList (FE-5.1)", () => {
  it("renders skeleton cards while loading", () => {
    renderComponent();
    expect(screen.getAllByTestId("skeleton-job-card")).toHaveLength(5);
  });

  it("renders job cards from shortlist data", async () => {
    renderComponent();
    await waitFor(() => {
      expect(screen.getByText("Frontend Engineer")).toBeInTheDocument();
      expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
      expect(screen.getByText("Full Stack Dev")).toBeInTheDocument();
    });
  });

  it("shows empty state when no shortlist", async () => {
    jobsData = null;
    renderComponent();

    await waitFor(() => {
      expect(
        screen.getByText(/Add your target roles in your profile/i)
      ).toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: /Update profile/i })).toBeInTheDocument();
  });

  it("renders job cards with fit scores", async () => {
    renderComponent();
    await waitFor(() => {
      expect(screen.getByText("90% fit")).toBeInTheDocument();
    });
  });
});
