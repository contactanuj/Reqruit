// ResumeVersionList.test.tsx — FE-4.5 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResumeVersionList } from "./ResumeVersionList";

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

const mockResumes = [
  {
    id: "resume-1",
    filename: "master-resume.pdf",
    uploadedAt: "2024-01-15T10:00:00Z",
    parseStatus: "completed",
    isMaster: true,
  },
  {
    id: "resume-2",
    filename: "tailored-resume.pdf",
    uploadedAt: "2024-02-20T14:00:00Z",
    parseStatus: "completed",
    isMaster: false,
  },
];

const handlers = [
  http.get("http://localhost:8000/resumes", () => {
    return HttpResponse.json(mockResumes);
  }),
  http.patch("http://localhost:8000/resumes/:id", () => {
    return HttpResponse.json({ success: true });
  }),
  http.delete("http://localhost:8000/resumes/:id", () => {
    return new HttpResponse(null, { status: 204 });
  }),
];

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
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
      <ResumeVersionList locale="IN" />
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ResumeVersionList (FE-4.5)", () => {
  it("renders resume list with master badge", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("master-resume.pdf")).toBeInTheDocument();
    });

    // "Master" badge should be visible as an exact badge label
    const masterBadges = screen.getAllByText("Master");
    expect(masterBadges.length).toBeGreaterThan(0);
    expect(screen.getByText("tailored-resume.pdf")).toBeInTheDocument();
  });

  it("blocks deleting the master resume with inline message", async () => {
    const user = userEvent.setup();
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("master-resume.pdf")).toBeInTheDocument();
    });

    // Find and click delete on master resume (resume-1)
    const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
    await user.click(deleteButtons[0]); // First delete button is for master

    expect(
      screen.getByText(/cannot delete the master resume/i)
    ).toBeInTheDocument();
  });

  it("shows 'Set as master' only on non-master resumes", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("tailored-resume.pdf")).toBeInTheDocument();
    });

    // Only one "Set as master" button should exist (for non-master resume)
    const setMasterButtons = screen.getAllByRole("button", { name: /set as master/i });
    expect(setMasterButtons).toHaveLength(1);
  });

  it("calls DELETE when confirming delete of non-master resume", async () => {
    let deleteCalledId: string | null = null;
    server.use(
      http.delete("http://localhost:8000/resumes/:id", ({ params }) => {
        deleteCalledId = params.id as string;
        return new HttpResponse(null, { status: 204 });
      })
    );

    const user = userEvent.setup();
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("tailored-resume.pdf")).toBeInTheDocument();
    });

    // Find the delete button for the non-master resume
    const deleteButtons = screen.getAllByRole("button", { name: /delete/i });
    await user.click(deleteButtons[1]); // Second button for non-master

    // Confirm dialog should appear
    const confirmButton = await screen.findByRole("button", { name: /confirm/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(deleteCalledId).toBe("resume-2");
    });
  });
});
