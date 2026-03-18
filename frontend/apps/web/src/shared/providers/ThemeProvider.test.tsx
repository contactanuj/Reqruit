// ThemeProvider.test.tsx — FE-2.4 (AC: #1, #2)

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, act } from "@testing-library/react";
import { ThemeProvider } from "./ThemeProvider";
import { useThemeStore } from "@/features/shell/store/theme-store";

beforeEach(() => {
  // Reset store and DOM
  useThemeStore.setState({ theme: "system" });
  document.documentElement.classList.remove("dark");
  localStorage.clear();
});

describe("ThemeProvider", () => {
  it("applies dark class when theme is dark", () => {
    useThemeStore.setState({ theme: "dark" });
    render(<ThemeProvider><div /></ThemeProvider>);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("removes dark class when theme is light", () => {
    document.documentElement.classList.add("dark");
    useThemeStore.setState({ theme: "light" });
    render(<ThemeProvider><div /></ThemeProvider>);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("persists theme preference to localStorage", () => {
    act(() => {
      useThemeStore.getState().setTheme("dark");
    });
    const stored = localStorage.getItem("reqruit-theme");
    expect(stored).not.toBeNull();
    const parsed = JSON.parse(stored!);
    expect(parsed.state.theme).toBe("dark");
  });

  it("applies dark mode when OS prefers dark and theme is system", () => {
    const originalMatchMedia = window.matchMedia;
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: query === "(prefers-color-scheme: dark)",
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        onchange: null,
        dispatchEvent: vi.fn(),
      })),
    });

    useThemeStore.setState({ theme: "system" });
    render(<ThemeProvider><div /></ThemeProvider>);
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    // Restore original matchMedia
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: originalMatchMedia,
    });
  });

  it("renders children", () => {
    const { getByText } = render(
      <ThemeProvider><span>Hello</span></ThemeProvider>,
    );
    expect(getByText("Hello")).toBeInTheDocument();
  });
});
