// ProfileEditor.test.tsx — FE-4.4 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProfileEditor } from "./ProfileEditor";
import type { Profile } from "../types";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/profile",
}));

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

const handlers = [
  http.patch("http://localhost:8000/users/me/profile", async ({ request }) => {
    const body = await request.json() as Record<string, unknown>;
    if (body.headline === "TRIGGER_422") {
      return HttpResponse.json(
        { detail: [{ loc: ["body", "headline"], msg: "Value too long" }] },
        { status: 422 }
      );
    }
    return HttpResponse.json({
      id: "user-1",
      contact: { name: "Jane Smith", email: "jane@example.com" },
      headline: body.headline ?? "Senior Engineer",
      summary: body.summary ?? "Experienced engineer",
      experience: [],
      education: [],
      skills: [],
      targetRoles: [],
      targetCompanies: [],
    });
  }),
  http.get("http://localhost:8000/users/me/profile", () => {
    return HttpResponse.json({
      id: "user-1",
      contact: { name: "Jane Smith", email: "jane@example.com" },
      headline: "Senior Engineer",
      summary: "Experienced engineer",
      experience: [],
      education: [],
      skills: [],
      targetRoles: [],
      targetCompanies: [],
    });
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
// Fixtures
// ---------------------------------------------------------------------------

const mockProfile: Profile = {
  id: "user-1",
  contact: { name: "Jane Smith", email: "jane@example.com" },
  headline: "Senior Engineer",
  summary: "Experienced engineer",
  experience: [],
  education: [],
  skills: [],
  targetRoles: [],
  targetCompanies: [],
};

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderComponent(onClose?: () => void, locale: "IN" | "US" = "IN") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <ProfileEditor profile={mockProfile} onClose={onClose} locale={locale} />
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ProfileEditor (FE-4.4)", () => {
  it("renders form with headline and summary fields", () => {
    renderComponent();

    expect(screen.getByLabelText(/headline/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/summary/i)).toBeInTheDocument();
  });

  it("shows LPA label for IN locale salary field", () => {
    renderComponent(undefined, "IN");
    expect(screen.getByText(/lpa/i)).toBeInTheDocument();
  });

  it("shows USD label for US locale salary field", () => {
    renderComponent(undefined, "US");
    expect(screen.getByText(/usd/i)).toBeInTheDocument();
  });

  it("submits form and calls onClose on success", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderComponent(onClose);

    const headlineInput = screen.getByLabelText(/headline/i);
    await user.clear(headlineInput);
    await user.type(headlineInput, "Updated headline");

    await user.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => {
      expect(mockToastSuccess).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
  });
});
