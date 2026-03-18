import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSilentRefresh } from "./useSilentRefresh";
import { useAuthStore } from "../store/auth-store";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock signOut from next-auth/react
vi.mock("next-auth/react", () => ({
  signOut: vi.fn().mockResolvedValue(undefined),
}));

// ---------------------------------------------------------------------------
// Helper: build a fake JWT with a specific exp
// ---------------------------------------------------------------------------

function makeJwt(expiresInSeconds: number): string {
  const payload = {
    exp: Math.floor(Date.now() / 1000) + expiresInSeconds,
    sub: "user-1",
  };
  // base64url encode (no padding)
  const encoded = btoa(JSON.stringify(payload))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
  return `eyJhbGciOiJIUzI1NiJ9.${encoded}.signature`;
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal("fetch", vi.fn());
  mockPush.mockClear();
  // Reset auth store between tests
  useAuthStore.setState({ accessToken: null, isAuthenticated: false });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// AC#1 — Proactive refresh before expiry
// ---------------------------------------------------------------------------

describe("useSilentRefresh — proactive refresh (AC#1)", () => {
  it("calls /auth/refresh when token expires in < 60s", async () => {
    const token = makeJwt(30); // expires in 30s (within the 60s threshold)
    useAuthStore.setState({ accessToken: token, isAuthenticated: true });

    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ access_token: "new_tok", token_type: "bearer" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    renderHook(() => useSilentRefresh());

    // Should be called immediately (delay ≤ 0)
    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/auth/refresh"),
      expect.objectContaining({ method: "POST", credentials: "include" })
    );
  });

  it("updates Zustand access token after successful refresh", async () => {
    const token = makeJwt(30);
    useAuthStore.setState({ accessToken: token, isAuthenticated: true });

    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ access_token: "refreshed_tok", token_type: "bearer" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    renderHook(() => useSilentRefresh());

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(useAuthStore.getState().accessToken).toBe("refreshed_tok");
  });

  it("schedules refresh 60s before expiry when token is not near expiry", async () => {
    const token = makeJwt(120); // 120s from now
    useAuthStore.setState({ accessToken: token, isAuthenticated: true });

    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ access_token: "new_tok", token_type: "bearer" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    renderHook(() => useSilentRefresh());

    // Should NOT be called immediately
    await act(async () => {
      await vi.advanceTimersByTimeAsync(59_000);
    });
    expect(fetch).not.toHaveBeenCalled();

    // Should be called after 60s (120 - 60 = 60s delay)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_100);
    });
    expect(fetch).toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// AC#2 — Refresh failure → clear auth + redirect
// ---------------------------------------------------------------------------

describe("useSilentRefresh — refresh failure (AC#2)", () => {
  it("clears auth store when refresh fails", async () => {
    const token = makeJwt(30);
    useAuthStore.setState({ accessToken: token, isAuthenticated: true });

    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "Refresh token expired" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      })
    );

    renderHook(() => useSilentRefresh());

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("redirects to /login when refresh fails", async () => {
    const token = makeJwt(30);
    useAuthStore.setState({ accessToken: token, isAuthenticated: true });

    vi.mocked(fetch).mockRejectedValue(new Error("Network error"));

    renderHook(() => useSilentRefresh());

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(mockPush).toHaveBeenCalledWith("/login");
  });
});

// ---------------------------------------------------------------------------
// AC#1 — Tab focus trigger
// ---------------------------------------------------------------------------

describe("useSilentRefresh — tab focus (AC#1)", () => {
  it("triggers refresh on tab focus when token is near expiry", async () => {
    const token = makeJwt(30);
    useAuthStore.setState({ accessToken: token, isAuthenticated: true });

    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ access_token: "new_tok", token_type: "bearer" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    renderHook(() => useSilentRefresh());

    // Simulate initial render consumed the first call
    await act(async () => {
      await vi.runAllTimersAsync();
    });

    const callCount = vi.mocked(fetch).mock.calls.length;

    // Update token to near-expiry for visibility test
    const nearExpiryToken = makeJwt(30);
    useAuthStore.setState({ accessToken: nearExpiryToken, isAuthenticated: true });

    // Simulate tab becoming visible
    await act(async () => {
      Object.defineProperty(document, "visibilityState", {
        value: "visible",
        configurable: true,
      });
      document.dispatchEvent(new Event("visibilitychange"));
      await vi.runAllTimersAsync();
    });

    expect(vi.mocked(fetch).mock.calls.length).toBeGreaterThan(callCount);
  });
});

// ---------------------------------------------------------------------------
// AC#1 — No action when no token
// ---------------------------------------------------------------------------

describe("useSilentRefresh — idle when no token", () => {
  it("does not call refresh when no access token", async () => {
    useAuthStore.setState({ accessToken: null, isAuthenticated: false });

    renderHook(() => useSilentRefresh());

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(fetch).not.toHaveBeenCalled();
  });
});
