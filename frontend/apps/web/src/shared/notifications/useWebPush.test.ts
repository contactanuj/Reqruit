import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useWebPush } from "./useWebPush";

// Mock apiClient
vi.mock("@reqruit/api-client", () => ({
  apiClient: {
    post: vi.fn().mockResolvedValue({}),
    delete: vi.fn().mockResolvedValue({}),
  },
}));

import { apiClient } from "@reqruit/api-client";

const mockSubscription = {
  toJSON: vi.fn().mockReturnValue({
    endpoint: "https://push.example.com/sub123",
    keys: { auth: "auth-key", p256dh: "p256dh-key" },
  }),
  unsubscribe: vi.fn().mockResolvedValue(true),
};

const mockPushManager = {
  subscribe: vi.fn().mockResolvedValue(mockSubscription),
  getSubscription: vi.fn().mockResolvedValue(null),
};

const mockServiceWorkerRegistration = {
  pushManager: mockPushManager,
};

function setupMocks(permission: NotificationPermission = "default") {
  // Mock Notification
  Object.defineProperty(window, "Notification", {
    writable: true,
    configurable: true,
    value: {
      permission,
      requestPermission: vi.fn().mockResolvedValue(permission),
    },
  });

  // Mock PushManager
  Object.defineProperty(window, "PushManager", {
    writable: true,
    configurable: true,
    value: class PushManager {},
  });

  // Mock serviceWorker
  Object.defineProperty(navigator, "serviceWorker", {
    writable: true,
    configurable: true,
    value: {
      ready: Promise.resolve(mockServiceWorkerRegistration),
    },
  });
}

describe("useWebPush", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Re-setup mocks after clearAllMocks (clearAllMocks resets implementations)
    mockSubscription.toJSON.mockReturnValue({
      endpoint: "https://push.example.com/sub123",
      keys: { auth: "auth-key", p256dh: "p256dh-key" },
    });
    mockSubscription.unsubscribe.mockResolvedValue(true);
    mockPushManager.getSubscription.mockResolvedValue(null);
    mockPushManager.subscribe.mockResolvedValue(mockSubscription);
    vi.mocked(apiClient.post).mockResolvedValue({});
    vi.mocked(apiClient.delete).mockResolvedValue({});
  });

  afterEach(() => {
    // Only restore window event listener spies (not navigator/window property overrides)
    vi.clearAllMocks();
  });

  it("detects push support when APIs are available", () => {
    setupMocks("default");
    const { result } = renderHook(() => useWebPush());
    expect(result.current.isSupported).toBe(true);
  });

  it("subscribe calls POST /notifications/subscribe", async () => {
    setupMocks("granted");
    const { result } = renderHook(() => useWebPush());

    await act(async () => {
      await result.current.subscribe();
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      "/notifications/subscribe",
      expect.objectContaining({ endpoint: expect.any(String) })
    );
  });

  it("subscribe registers push subscription with POST /notifications/subscribe", async () => {
    setupMocks("granted");
    const { result } = renderHook(() => useWebPush());

    // Ensure isSupported before subscribing
    expect(result.current.isSupported).toBe(true);

    await act(async () => {
      await result.current.subscribe();
    });

    // Verify apiClient.post was called (proves subscribe ran to completion)
    expect(vi.mocked(apiClient.post)).toHaveBeenCalledWith(
      "/notifications/subscribe",
      expect.any(Object)
    );
  });

  it("returns error when subscribe fails", async () => {
    setupMocks("granted");
    mockPushManager.subscribe.mockRejectedValueOnce(
      new Error("Permission denied")
    );

    const { result } = renderHook(() => useWebPush());

    await act(async () => {
      await result.current.subscribe();
    });

    expect(result.current.error).toBe("Permission denied");
    expect(result.current.isSubscribed).toBe(false);
  });

  it("isSubscribed starts as false when no existing subscription", () => {
    setupMocks("granted");
    // getSubscription returns null (set in beforeEach)

    const { result } = renderHook(() => useWebPush());

    // Initially false
    expect(result.current.isSubscribed).toBe(false);
  });

  it("permission reflects Notification.permission", () => {
    setupMocks("denied");
    const { result } = renderHook(() => useWebPush());
    expect(result.current.permission).toBe("denied");
  });
});
