import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LoginForm } from "./LoginForm";

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
  http.post("http://localhost:8000/auth/login", async ({ request }) => {
    const body = await request.json() as { email: string; password: string };
    if (body.email === "wrong@example.com") {
      return HttpResponse.json({ detail: "Invalid credentials" }, { status: 401 });
    }
    return HttpResponse.json({ access_token: "tok_login123", token_type: "bearer" });
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

function renderForm(redirectTo?: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <LoginForm redirectTo={redirectTo} />
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// AC#1 — Valid login
// ---------------------------------------------------------------------------

describe("LoginForm — valid credentials (AC#1)", () => {
  it("calls POST /auth/login and redirects to /dashboard by default", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/email/i), "user@example.com");
    await user.type(screen.getByLabelText(/password/i), "mypassword");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(mockSignIn).toHaveBeenCalledWith("credentials", {
      accessToken: "tok_login123",
      redirect: false,
    }));
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/dashboard"));
  });

  it("redirects to ?redirect= destination when present", async () => {
    const user = userEvent.setup();
    renderForm("/jobs");

    await user.type(screen.getByLabelText(/email/i), "user@example.com");
    await user.type(screen.getByLabelText(/password/i), "mypassword");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/jobs"));
  });
});

// ---------------------------------------------------------------------------
// AC#2 — 401: form-level error only
// ---------------------------------------------------------------------------

describe("LoginForm — invalid credentials (AC#2)", () => {
  it("shows form-level error on 401 — no field-specific errors", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/email/i), "wrong@example.com");
    await user.type(screen.getByLabelText(/password/i), "badpassword");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/incorrect email or password/i)
      ).toBeInTheDocument()
    );
  });

  it("does not show field-level errors on 401", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/email/i), "wrong@example.com");
    await user.type(screen.getByLabelText(/password/i), "badpassword");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() =>
      screen.getByText(/incorrect email or password/i)
    );

    // Form-level error only — email and password fields should NOT have individual errors
    expect(screen.queryByText(/please enter a valid email/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/password must be/i)).not.toBeInTheDocument();
  });

  it("does not redirect on 401", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText(/email/i), "wrong@example.com");
    await user.type(screen.getByLabelText(/password/i), "badpassword");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() =>
      screen.getByText(/incorrect email or password/i)
    );
    expect(mockPush).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// AC#4 — Middleware redirect (unit-test the middleware function)
// ---------------------------------------------------------------------------

describe("middleware — route protection (AC#4)", () => {
  it("redirects unauthenticated request to /login with redirect param", async () => {
    const { middleware } = await import("@/middleware");
    const { NextRequest } = await import("next/server");

    const req = new NextRequest("http://localhost/dashboard");
    const res = middleware(req);

    expect(res.status).toBe(307);
    const location = res.headers.get("location") ?? "";
    expect(location).toMatch(/\/login/);
    expect(location).toMatch(/redirect=%2Fdashboard/);
  });

  it("redirects authenticated user away from /login to /dashboard", async () => {
    const { middleware } = await import("@/middleware");
    const { NextRequest } = await import("next/server");

    const req = new NextRequest("http://localhost/login", {
      headers: { cookie: "next-auth.session-token=valid-token" },
    });
    const res = middleware(req);

    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toMatch(/\/dashboard/);
  });
});
