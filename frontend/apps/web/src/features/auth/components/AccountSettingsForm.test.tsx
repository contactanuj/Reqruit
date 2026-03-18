import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AccountSettingsForm } from "./AccountSettingsForm";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// ---------------------------------------------------------------------------
// MSW server
// ---------------------------------------------------------------------------

const handlers = [
  http.get("http://localhost:8000/users/me", () =>
    HttpResponse.json({ email: "alice@example.com", id: "u1" })
  ),

  http.patch("http://localhost:8000/users/me", async ({ request }) => {
    const body = await request.json() as Record<string, string>;

    // Simulate wrong current password
    if (body.current_password === "wrongpass") {
      return HttpResponse.json(
        { detail: "Current password is incorrect" },
        { status: 422 }
      );
    }
    return HttpResponse.json({ email: body.email ?? "alice@example.com", id: "u1" });
  }),
];

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());
afterEach(() => server.resetHandlers());

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderForm() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <AccountSettingsForm />
      <Toaster />
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// AC#2 — Email update
// ---------------------------------------------------------------------------

describe("AccountSettingsForm — email update (AC#2)", () => {
  it("shows success toast after email update", async () => {
    const user = userEvent.setup();
    renderForm();

    // Wait for form to be rendered with current email
    const emailInput = await screen.findByLabelText(/new email/i);
    await user.clear(emailInput);
    await user.type(emailInput, "bob@example.com");
    await user.click(screen.getByRole("button", { name: /update email/i }));

    await waitFor(() =>
      expect(screen.getByText(/email updated successfully/i)).toBeInTheDocument()
    );
  });
});

// ---------------------------------------------------------------------------
// AC#3 — Wrong current password shows inline error
// ---------------------------------------------------------------------------

describe("AccountSettingsForm — password change (AC#3)", () => {
  it("shows inline error when current password is incorrect", async () => {
    const user = userEvent.setup();
    renderForm();

    const currentPw = await screen.findByLabelText(/current password/i);
    const newPw = screen.getByLabelText(/^new password/i);
    const confirmPw = screen.getByLabelText(/confirm new password/i);

    await user.type(currentPw, "wrongpass");
    await user.type(newPw, "NewPass123!");
    await user.type(confirmPw, "NewPass123!");
    await user.click(screen.getByRole("button", { name: /update password/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/current password is incorrect/i)
      ).toBeInTheDocument()
    );
  });
});

// ---------------------------------------------------------------------------
// AC#4 — Password mismatch blur validation
// ---------------------------------------------------------------------------

describe("AccountSettingsForm — password mismatch (AC#4)", () => {
  it("shows 'Passwords do not match' on confirm field blur when mismatch", async () => {
    const user = userEvent.setup();
    renderForm();

    const newPw = await screen.findByLabelText(/^new password/i);
    const confirmPw = screen.getByLabelText(/confirm new password/i);

    await user.type(newPw, "NewPass123!");
    await user.type(confirmPw, "Different!");
    await user.tab(); // blur confirm field

    await waitFor(() =>
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
    );
  });
});
