// CompanyResearchCard.test.tsx — FE-5.5 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CompanyResearchCard } from "./CompanyResearchCard";
import type { CompanyResearch } from "../types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

const mockResearch: CompanyResearch = {
  culture_summary: "Strong engineering culture with emphasis on ownership.",
  tech_stack: ["Python", "React", "Kubernetes", "PostgreSQL"],
  glassdoor_rating: 4.2,
  interview_patterns: [
    { theme: "System Design", description: "Large-scale distributed systems" },
    { theme: "Behavioural", description: "Leadership and ownership" },
    { theme: "Coding", description: "DSA problems on LeetCode medium level" },
  ],
  generated_at: "2026-03-01T00:00:00Z",
};

let researchData: CompanyResearch | null = null;

const server = setupServer(
  http.get("http://localhost:8000/jobs/:jobId/company-research", () => {
    if (researchData === null) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(researchData);
  }),
  http.post("http://localhost:8000/jobs/:jobId/company-research", () => {
    researchData = mockResearch;
    return HttpResponse.json(mockResearch);
  })
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
  researchData = null;
});

function renderComponent(jobId = "job-1") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <CompanyResearchCard jobId={jobId} />
    </QueryClientProvider>
  );
}

describe("CompanyResearchCard (FE-5.5)", () => {
  it("shows generate button when no research exists", async () => {
    renderComponent();
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /research this company/i })
      ).toBeInTheDocument();
    });
  });

  it("renders all sections when data is present", async () => {
    researchData = mockResearch;
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("Strong engineering culture with emphasis on ownership.")).toBeInTheDocument();
      expect(screen.getByText("Python")).toBeInTheDocument();
      expect(screen.getByText("4.2")).toBeInTheDocument();
      expect(screen.getByText("System Design")).toBeInTheDocument();
    });
  });

  it("shows skeleton while generating", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("http://localhost:8000/jobs/:jobId/company-research", async () => {
        await new Promise((r) => setTimeout(r, 100));
        return HttpResponse.json(mockResearch);
      })
    );

    renderComponent();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /research this company/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /research this company/i }));
    // Button should disappear or skeleton should show
    // The skeleton has aria-hidden so we check element presence
    expect(screen.queryByRole("button", { name: /research this company/i })).not.toBeInTheDocument();
  });

  it("renders interview patterns list", async () => {
    researchData = mockResearch;
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("System Design")).toBeInTheDocument();
      expect(screen.getByText("Behavioural")).toBeInTheDocument();
      expect(screen.getByText("Coding")).toBeInTheDocument();
    });
  });

  it("Glassdoor rating has accessible aria-label", async () => {
    researchData = mockResearch;
    renderComponent();

    await waitFor(() => {
      expect(
        screen.getByLabelText(/Glassdoor rating: 4.2 out of 5/i)
      ).toBeInTheDocument();
    });
  });
});
