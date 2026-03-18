// layout-store.test.ts — FE-2.1 (AC: #2, #4)

import { describe, it, expect, beforeEach } from "vitest";
import { useLayoutStore } from "./layout-store";

beforeEach(() => {
  // Reset store state before each test
  useLayoutStore.setState({
    sidebarCollapsed: false,
    copilotVisible: true,
    shortcutsOverlayVisible: false,
  });
  localStorage.clear();
});

describe("useLayoutStore", () => {
  it("has expected initial state", () => {
    const state = useLayoutStore.getState();
    expect(state.sidebarCollapsed).toBe(false);
    expect(state.copilotVisible).toBe(true);
  });

  it("toggleSidebar flips sidebarCollapsed", () => {
    const { toggleSidebar } = useLayoutStore.getState();
    toggleSidebar();
    expect(useLayoutStore.getState().sidebarCollapsed).toBe(true);
    toggleSidebar();
    expect(useLayoutStore.getState().sidebarCollapsed).toBe(false);
  });

  it("setSidebarCollapsed sets exact value", () => {
    useLayoutStore.getState().setSidebarCollapsed(true);
    expect(useLayoutStore.getState().sidebarCollapsed).toBe(true);
  });

  it("toggleCopilot flips copilotVisible", () => {
    const { toggleCopilot } = useLayoutStore.getState();
    toggleCopilot();
    expect(useLayoutStore.getState().copilotVisible).toBe(false);
  });

  it("persists to localStorage under reqruit-layout key", () => {
    useLayoutStore.getState().setSidebarCollapsed(true);
    const stored = localStorage.getItem("reqruit-layout");
    expect(stored).not.toBeNull();
    const parsed = JSON.parse(stored!);
    expect(parsed.state.sidebarCollapsed).toBe(true);
  });
});
