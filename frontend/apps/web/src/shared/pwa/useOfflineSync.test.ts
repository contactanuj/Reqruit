import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { useOfflineSync } from "./useOfflineSync";

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    info: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock useMutationState
vi.mock("@tanstack/react-query", async (importOriginal) => {
  const original = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...original,
    useMutationState: vi.fn().mockReturnValue([]),
  };
});

import { useMutationState } from "@tanstack/react-query";
import { toast } from "sonner";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  queryClient.resumePausedMutations = vi.fn().mockResolvedValue(undefined);

  const wrapper = ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);

  return { wrapper, queryClient };
}

describe("useOfflineSync", () => {
  const originalOnLine = Object.getOwnPropertyDescriptor(navigator, "onLine");

  function setOnline(value: boolean) {
    Object.defineProperty(navigator, "onLine", {
      writable: true,
      configurable: true,
      value,
    });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    setOnline(true);
    vi.mocked(useMutationState).mockReturnValue([]);
  });

  afterEach(() => {
    if (originalOnLine) {
      Object.defineProperty(navigator, "onLine", originalOnLine);
    }
  });

  it("returns isOnline=true when navigator.onLine=true", () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useOfflineSync(), { wrapper });
    expect(result.current.isOnline).toBe(true);
  });

  it("returns isOnline=false when offline event fires", () => {
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useOfflineSync(), { wrapper });

    act(() => {
      setOnline(false);
      window.dispatchEvent(new Event("offline"));
    });

    expect(result.current.isOnline).toBe(false);
  });

  it("returns hasPendingMutations=false when no paused mutations", () => {
    vi.mocked(useMutationState).mockReturnValue([]);
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useOfflineSync(), { wrapper });
    expect(result.current.hasPendingMutations).toBe(false);
    expect(result.current.pendingCount).toBe(0);
  });

  it("returns hasPendingMutations=true when paused mutations exist", () => {
    vi.mocked(useMutationState).mockReturnValue([
      { isPaused: true, status: "pending" } as ReturnType<typeof useMutationState>[number],
      { isPaused: true, status: "pending" } as ReturnType<typeof useMutationState>[number],
    ]);
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useOfflineSync(), { wrapper });
    expect(result.current.hasPendingMutations).toBe(true);
    expect(result.current.pendingCount).toBe(2);
  });

  it("updates isOnline when online event fires", () => {
    setOnline(false);
    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useOfflineSync(), { wrapper });

    expect(result.current.isOnline).toBe(false);

    act(() => {
      setOnline(true);
      window.dispatchEvent(new Event("online"));
    });

    expect(result.current.isOnline).toBe(true);
  });
});
