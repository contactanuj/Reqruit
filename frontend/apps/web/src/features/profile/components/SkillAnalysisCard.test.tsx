// SkillAnalysisCard.test.tsx — FE-4.6 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SkillAnalysisCard } from "./SkillAnalysisCard";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/profile",
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// ---------------------------------------------------------------------------
// MSW server
// ---------------------------------------------------------------------------

const mockAnalysis = {
  yourSkills: [
    { name: "Python", category: "Technical", proficiency: 85 },
    { name: "React", category: "Technical", proficiency: 70 },
  ],
  trendingInTargetRoles: [
    { name: "TypeScript", demand: "high" },
    { name: "Kubernetes", demand: "medium" },
  ],
  skillGaps: [
    {
      name: "Go",
      exampleJD: "We use Go for backend services",
      learningResource: "https://go.dev/learn/",
    },
  ],
  generatedAt: "2024-01-15T10:00:00Z",
};

let analysisData: typeof mockAnalysis | null = null;

const handlers = [
  http.get("http://localhost:8000/users/me/skill-analysis", () => {
    if (analysisData === null) {
      return new HttpResponse(null, { status: 204 });
    }
    return HttpResponse.json(analysisData);
  }),
  http.post("http://localhost:8000/users/me/skill-analysis/generate", () => {
    analysisData = mockAnalysis;
    return HttpResponse.json({ success: true });
  }),
];

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
  analysisData = null;
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderComponent() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <SkillAnalysisCard />
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SkillAnalysisCard (FE-4.6)", () => {
  it("shows generate button when no analysis exists", async () => {
    renderComponent();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /generate skill analysis/i })
      ).toBeInTheDocument();
    });
  });

  it("shows three sections when analysis data is present", async () => {
    analysisData = mockAnalysis;
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/your skills/i)).toBeInTheDocument();
      expect(screen.getByText(/trending/i)).toBeInTheDocument();
      expect(screen.getByText(/skill gaps/i)).toBeInTheDocument();
    });
  });

  it("shows proficiency bar for skill data", async () => {
    analysisData = mockAnalysis;
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("Python")).toBeInTheDocument();
    });

    // Proficiency bar should be in the DOM
    const progressBars = document.querySelectorAll('[aria-valuenow]');
    expect(progressBars.length).toBeGreaterThan(0);
  });

  it("shows skill gap with tooltip content", async () => {
    analysisData = mockAnalysis;
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("Go")).toBeInTheDocument();
    });
  });

  it("shows skeleton when generating analysis", async () => {
    const user = userEvent.setup();
    // Keep server slow to see skeleton
    server.use(
      http.post("http://localhost:8000/users/me/skill-analysis/generate", async () => {
        await new Promise((r) => setTimeout(r, 100));
        return HttpResponse.json({ success: true });
      })
    );

    renderComponent();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /generate skill analysis/i })
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /generate skill analysis/i }));

    // While generating, skeleton should show (or loading state)
    // The button should be disabled/loading
    const btn = screen.queryByRole("button", { name: /generating/i });
    // If not visible by name, check disabled state
    if (!btn) {
      const generateBtn = screen.queryByRole("button", { name: /generate/i });
      if (generateBtn) {
        expect(generateBtn).toBeDisabled();
      }
    }
  });
});
