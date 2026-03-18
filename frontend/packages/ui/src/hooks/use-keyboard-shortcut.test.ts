// use-keyboard-shortcut.test.ts — FE-2.5 (AC: #1, #2, #3, #4)

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useKeyboardShortcuts } from "./use-keyboard-shortcut";
import type { ShortcutDefinition } from "./use-keyboard-shortcut";

function fireKey(key: string, opts: Partial<KeyboardEventInit> = {}) {
  const event = new KeyboardEvent("keydown", { key, bubbles: true, ...opts });
  document.dispatchEvent(event);
  return event;
}

beforeEach(() => {
  // Simulate desktop viewport
  Object.defineProperty(window, "innerWidth", {
    writable: true,
    configurable: true,
    value: 1280,
  });
});

afterEach(() => {
  vi.clearAllTimers();
});

describe("useKeyboardShortcuts", () => {
  it("fires action on single key", () => {
    const action = vi.fn();
    const shortcuts: ShortcutDefinition[] = [
      { key: "?", description: "Show shortcuts", action },
    ];
    renderHook(() => useKeyboardShortcuts(shortcuts));
    fireKey("?");
    expect(action).toHaveBeenCalledOnce();
  });

  it("fires action on meta+key shortcut", () => {
    const action = vi.fn();
    const shortcuts: ShortcutDefinition[] = [
      { key: "k", meta: true, description: "Command palette", action },
    ];
    renderHook(() => useKeyboardShortcuts(shortcuts));
    fireKey("k", { ctrlKey: true });
    expect(action).toHaveBeenCalledOnce();
  });

  it("fires chord action (G then J)", () => {
    vi.useFakeTimers();
    const action = vi.fn();
    const shortcuts: ShortcutDefinition[] = [
      { key: "g", chord: "j", description: "Go to jobs", action },
    ];
    renderHook(() => useKeyboardShortcuts(shortcuts));
    fireKey("g");
    fireKey("j");
    expect(action).toHaveBeenCalledOnce();
    vi.useRealTimers();
  });

  it("does not fire chord if second key is not pressed within timeout", () => {
    vi.useFakeTimers();
    const action = vi.fn();
    const shortcuts: ShortcutDefinition[] = [
      { key: "g", chord: "j", description: "Go to jobs", action },
    ];
    renderHook(() => useKeyboardShortcuts(shortcuts));
    fireKey("g");
    vi.advanceTimersByTime(1500);
    fireKey("j");
    expect(action).not.toHaveBeenCalled();
    vi.useRealTimers();
  });

  it("does not fire shortcuts when inside an input element", () => {
    const action = vi.fn();
    const shortcuts: ShortcutDefinition[] = [
      { key: "[", description: "Collapse sidebar", action },
    ];
    renderHook(() => useKeyboardShortcuts(shortcuts));

    const input = document.createElement("input");
    document.body.appendChild(input);
    input.focus();

    const event = new KeyboardEvent("keydown", {
      key: "[",
      bubbles: true,
    });
    // Override target to be the input
    Object.defineProperty(event, "target", { value: input });
    document.dispatchEvent(event);

    expect(action).not.toHaveBeenCalled();
    document.body.removeChild(input);
  });

  it("does not fire shortcuts on mobile (innerWidth < 768)", () => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 375,
    });
    const action = vi.fn();
    const shortcuts: ShortcutDefinition[] = [
      { key: "?", description: "Show shortcuts", action },
    ];
    renderHook(() => useKeyboardShortcuts(shortcuts));
    fireKey("?");
    expect(action).not.toHaveBeenCalled();
  });
});
