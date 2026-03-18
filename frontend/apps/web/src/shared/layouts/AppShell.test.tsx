// AppShell.test.tsx — FE-2.1 (AC: #1, #2, #5)

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AppShell } from "./AppShell";
import { useLayoutStore } from "@/features/shell/store/layout-store";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/dashboard",
}));

// Mock auth hook to avoid real mutation setup
vi.mock("@/features/auth/hooks/useAuth", () => ({
  useLogout: () => ({ mutate: vi.fn(), isPending: false }),
}));

// Mock @repo/ui/hooks
vi.mock("@repo/ui/hooks", () => ({
  useSSEStream: () => ({ state: { status: "idle" }, cancel: vi.fn(), retry: vi.fn() }),
  useKeyboardShortcuts: vi.fn(),
}));

// Mock theme store — return full state object (called without selector)
vi.mock("@/features/shell/store/theme-store", () => ({
  useThemeStore: () => ({ theme: "system", setTheme: () => {} }),
}));

// Mock gamification and credits hooks to avoid QueryClient requirement
vi.mock("@/features/gamification/hooks/useGamification", () => ({
  useGamificationStatus: () => ({ data: undefined }),
}));

// Mock XPWidget and CreditCounter directly since they need QueryClient via hooks
vi.mock("@/features/gamification/components/XPWidget", () => ({
  XPWidget: () => null,
}));

vi.mock("@/features/credits/components/CreditCounter", () => ({
  CreditCounter: () => null,
}));

// Mock OfflineBanner and DemoBanner
vi.mock("@/shared/layouts/OfflineBanner", () => ({
  OfflineBanner: () => null,
}));

vi.mock("@/shared/layouts/DemoBanner", () => ({
  DemoBanner: () => null,
}));

beforeEach(() => {
  useLayoutStore.setState({
    sidebarCollapsed: false,
    copilotVisible: true,
    shortcutsOverlayVisible: false,
  });
  localStorage.clear();
});

describe("AppShell", () => {
  it("renders the main content area", () => {
    render(<AppShell><div data-testid="page-content">Hello</div></AppShell>);
    expect(screen.getByTestId("page-content")).toBeInTheDocument();
  });

  it("renders the app-shell container", () => {
    render(<AppShell><div>content</div></AppShell>);
    expect(screen.getByTestId("app-shell")).toBeInTheDocument();
  });

  it("sidebar collapse toggle persists state to localStorage", () => {
    render(<AppShell><div>content</div></AppShell>);
    const toggleBtn = screen.getByRole("button", { name: /collapse sidebar/i });
    fireEvent.click(toggleBtn);
    expect(useLayoutStore.getState().sidebarCollapsed).toBe(true);
    const stored = localStorage.getItem("reqruit-layout");
    expect(stored).not.toBeNull();
  });

  it("renders sidebar navigation landmarks", () => {
    render(<AppShell><div>content</div></AppShell>);
    expect(
      screen.getByRole("navigation", { name: /primary navigation/i }),
    ).toBeInTheDocument();
  });
});
