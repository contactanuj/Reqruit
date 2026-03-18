import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { RegisterForm } from "./RegisterForm";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockSignIn = vi.fn().mockResolvedValue({ ok: true });
vi.mock("next-auth/react", () => ({
  signIn: (...args: unknown[]) => mockSignIn(...args),
}));

// ---------------------------------------------------------------------------
// MSW server
// ---------------------------------------------------------------------------

const handlers = [
  http.post("http://localhost:8000/auth/register", async ({ request }) => {
    const body = await request.json() as { email: string; password: string };
    if (body.email === "taken@example.com") {
      return HttpResponse.json(
        { detail: "Email already registered" },
        { status: 422 }
      );
    }
    if (body.email === "error@example.com") {
      return HttpResponse.json({}, { status: 502 });
    }
    return HttpResponse.json({ access_token: "tok_abc123", token_type: "bearer" });
  }),
];

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  mockPush.mockClear();
  mockSignIn.mockClear();
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderForm() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <Toaster />
      <RegisterForm />
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// AC#1 — Valid registration
// ---------------------------------------------------------------------------

describe("RegisterForm — valid registration (AC#1)", () => {
  it("calls POST /auth/register with email and password on valid submit", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/email/i), "new@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => expect(mockSignIn).toHaveBeenCalledWith("credentials", {
      accessToken: "tok_abc123",
      redirect: false,
    }));
  });

  it("redirects to /onboarding after successful registration", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/email/i), "new@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/onboarding"));
  });
});

// ---------------------------------------------------------------------------
// AC#2 — 422: email already exists
// ---------------------------------------------------------------------------

describe("RegisterForm — duplicate email (AC#2)", () => {
  it("shows inline email error when 422 is returned", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/email/i), "taken@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/an account with this email already exists/i)
      ).toBeInTheDocument()
    );
  });

  it("does not redirect on 422", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/email/i), "taken@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() =>
      screen.getByText(/an account with this email already exists/i)
    );
    expect(mockPush).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// AC#3 — Password blur validation
// ---------------------------------------------------------------------------

describe("RegisterForm — password blur validation (AC#3)", () => {
  it("shows password error on blur when password is fewer than 8 characters", async () => {
    const user = userEvent.setup();
    renderForm();

    const passwordField = screen.getByLabelText(/^password$/i);
    await user.type(passwordField, "short");
    await user.tab(); // triggers blur

    await waitFor(() =>
      expect(
        screen.getByText(/password must be at least 8 characters/i)
      ).toBeInTheDocument()
    );
  });

  it("does not submit form when password is too short (validates before submit)", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/email/i), "test@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "short");
    await user.type(screen.getByLabelText(/confirm password/i), "short");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    // No API call should be made
    expect(mockSignIn).not.toHaveBeenCalled();
    expect(mockPush).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// AC#5 — 502: service unavailable toast
// ---------------------------------------------------------------------------

describe("RegisterForm — 502 error toast (AC#5)", () => {
  it("shows toast on 502 error", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/email/i), "error@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/service temporarily unavailable/i)
      ).toBeInTheDocument()
    );
  });

  it("does not redirect on 502", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/email/i), "error@example.com");
    await user.type(screen.getByLabelText(/^password$/i), "securepass1");
    await user.type(screen.getByLabelText(/confirm password/i), "securepass1");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    await waitFor(() =>
      screen.getByText(/service temporarily unavailable/i)
    );
    expect(mockPush).not.toHaveBeenCalled();
  });
});
