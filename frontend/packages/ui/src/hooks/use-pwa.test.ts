import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePWA } from "./use-pwa";

// jsdom doesn't implement matchMedia — provide stub
if (typeof window !== "undefined" && !window.matchMedia) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

describe("usePWA", () => {
  let beforeInstallPromptHandler: ((e: Event) => void) | null = null;
  let appInstalledHandler: (() => void) | null = null;
  const originalAddEventListener = window.addEventListener.bind(window);
  const originalRemoveEventListener = window.removeEventListener.bind(window);

  beforeEach(() => {
    vi.clearAllMocks();
    // Spy on window event listeners
    vi.spyOn(window, "addEventListener").mockImplementation((type, handler) => {
      if (type === "beforeinstallprompt") {
        beforeInstallPromptHandler = handler as (e: Event) => void;
      } else if (type === "appinstalled") {
        appInstalledHandler = handler as () => void;
      }
    });
    vi.spyOn(window, "removeEventListener").mockImplementation(() => {});
  });

  afterEach(() => {
    beforeInstallPromptHandler = null;
    appInstalledHandler = null;
    vi.restoreAllMocks();
  });

  it("initialises with canInstall=false before prompt event", () => {
    const { result } = renderHook(() => usePWA());
    expect(result.current.canInstall).toBe(false);
  });

  it("captures beforeinstallprompt event and sets canInstall=true", () => {
    const { result } = renderHook(() => usePWA());

    const mockPrompt = vi.fn().mockResolvedValue(undefined);
    const mockUserChoice = Promise.resolve({ outcome: "accepted" as const });

    const fakeEvent = {
      preventDefault: vi.fn(),
      prompt: mockPrompt,
      userChoice: mockUserChoice,
      type: "beforeinstallprompt",
    } as unknown as Event;

    act(() => {
      beforeInstallPromptHandler?.(fakeEvent);
    });

    expect(result.current.canInstall).toBe(true);
  });

  it("promptInstall calls event.prompt()", async () => {
    const { result } = renderHook(() => usePWA());

    const mockPrompt = vi.fn().mockResolvedValue(undefined);
    const mockUserChoice = Promise.resolve({ outcome: "accepted" as const });

    const fakeEvent = {
      preventDefault: vi.fn(),
      prompt: mockPrompt,
      userChoice: mockUserChoice,
      type: "beforeinstallprompt",
    } as unknown as Event;

    act(() => {
      beforeInstallPromptHandler?.(fakeEvent);
    });

    await act(async () => {
      await result.current.promptInstall();
    });

    expect(mockPrompt).toHaveBeenCalled();
  });

  it("sets isInstalled=true after appinstalled event", () => {
    const { result } = renderHook(() => usePWA());

    act(() => {
      appInstalledHandler?.();
    });

    expect(result.current.isInstalled).toBe(true);
  });

  it("returns isIOS false for non-iOS user agent", () => {
    const { result } = renderHook(() => usePWA());
    // jsdom doesn't simulate iOS
    expect(result.current.isIOS).toBe(false);
  });
});
