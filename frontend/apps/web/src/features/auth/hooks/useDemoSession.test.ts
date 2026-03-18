import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDemoSession } from "./useDemoSession";
import { useAuthStore } from "../store/auth-store";

// Use vi.hoisted to avoid initialization order issues
const { mockPush } = vi.hoisted(() => ({
  mockPush: vi.fn(),
}));

// Mock API client
vi.mock("@reqruit/api-client", () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({ access_token: "demo-token-123" }),
  },
}));

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

import { apiClient } from "@reqruit/api-client";

describe("useDemoSession", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      accessToken: null,
      isAuthenticated: false,
      isDemoMode: false,
    });
  });

  it("startDemoSession calls GET /auth/demo-session", async () => {
    const { result } = renderHook(() => useDemoSession());

    await act(async () => {
      await result.current.startDemoSession();
    });

    expect(apiClient.get).toHaveBeenCalledWith("/auth/demo-session");
  });

  it("sets isDemoMode=true in auth store after demo login", async () => {
    const { result } = renderHook(() => useDemoSession());

    await act(async () => {
      await result.current.startDemoSession();
    });

    expect(useAuthStore.getState().isDemoMode).toBe(true);
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
  });

  it("redirects to /dashboard after demo login", async () => {
    const { result } = renderHook(() => useDemoSession());

    await act(async () => {
      await result.current.startDemoSession();
    });

    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });

  it("endDemoSession clears auth and redirects to /register", () => {
    useAuthStore.setState({ isDemoMode: true, isAuthenticated: true, accessToken: "demo-token" });

    const { result } = renderHook(() => useDemoSession());

    act(() => {
      result.current.endDemoSession();
    });

    expect(useAuthStore.getState().isDemoMode).toBe(false);
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(mockPush).toHaveBeenCalledWith("/register");
  });

  it("isDemoMode is false initially", () => {
    const { result } = renderHook(() => useDemoSession());
    expect(result.current.isDemoMode).toBe(false);
  });
});
