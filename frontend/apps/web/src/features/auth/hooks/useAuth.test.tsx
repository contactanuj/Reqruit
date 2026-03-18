import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { useLogout } from "./useAuth";
import { useAuthStore } from "../store/auth-store";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockSignOut = vi.fn().mockResolvedValue(undefined);
vi.mock("next-auth/react", () => ({
  signIn: vi.fn(),
  signOut: (...args: unknown[]) => mockSignOut(...args),
}));

// ---------------------------------------------------------------------------
// MSW server
// ---------------------------------------------------------------------------

const handlers = [
  http.post("http://localhost:8000/auth/logout", () =>
    HttpResponse.json({}, { status: 200 })
  ),
];

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  mockPush.mockClear();
  mockSignOut.mockClear();
  useAuthStore.setState({ accessToken: null, isAuthenticated: false });
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return {
    qc,
    wrapper: ({ children }: { children: React.ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children),
  };
}

// ---------------------------------------------------------------------------
// AC#1 — Logout clears auth store, calls signOut, redirects
// ---------------------------------------------------------------------------

describe("useLogout — successful logout (AC#1)", () => {
  it("calls POST /auth/logout", async () => {
    useAuthStore.setState({ accessToken: "tok", isAuthenticated: true });
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useLogout(), { wrapper });

    await act(async () => {
      result.current.mutate();
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it("clears the Zustand auth store on success", async () => {
    useAuthStore.setState({ accessToken: "tok", isAuthenticated: true });
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useLogout(), { wrapper });

    await act(async () => {
      result.current.mutate();
    });

    await waitFor(() => {
      expect(useAuthStore.getState().accessToken).toBeNull();
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });
  });

  it("calls NextAuth signOut to remove httpOnly cookie", async () => {
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useLogout(), { wrapper });

    await act(async () => {
      result.current.mutate();
    });

    await waitFor(() =>
      expect(mockSignOut).toHaveBeenCalledWith({ redirect: false })
    );
  });

  it("redirects to /login after logout", async () => {
    const { wrapper } = makeWrapper();

    const { result } = renderHook(() => useLogout(), { wrapper });

    await act(async () => {
      result.current.mutate();
    });

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/login"));
  });

  it("clears TanStack Query cache on logout", async () => {
    const { qc, wrapper } = makeWrapper();
    // Seed some cached data
    qc.setQueryData(["user"], { name: "Alice" });

    const { result } = renderHook(() => useLogout(), { wrapper });

    await act(async () => {
      result.current.mutate();
    });

    await waitFor(() => result.current.isSuccess);
    expect(qc.getQueryData(["user"])).toBeUndefined();
  });
});

// ---------------------------------------------------------------------------
// AC#2 — Middleware blocks post-logout back-navigation
// ---------------------------------------------------------------------------

describe("middleware — post-logout route protection (AC#2)", () => {
  it("redirects unauthenticated request to /dashboard to /login", async () => {
    const { middleware } = await import("@/middleware");
    const { NextRequest } = await import("next/server");

    const req = new NextRequest("http://localhost/dashboard");
    const res = middleware(req);

    expect(res.status).toBe(307);
    const location = res.headers.get("location") ?? "";
    expect(location).toMatch(/\/login/);
  });

  it("sets Cache-Control: no-store on authenticated route response", async () => {
    const { middleware } = await import("@/middleware");
    const { NextRequest } = await import("next/server");

    // Authenticated user accessing /dashboard — should get no-store header
    const req = new NextRequest("http://localhost/dashboard", {
      headers: { cookie: "next-auth.session-token=valid-token" },
    });
    const res = middleware(req);

    expect(res.headers.get("Cache-Control")).toBe("no-store");
  });
});
