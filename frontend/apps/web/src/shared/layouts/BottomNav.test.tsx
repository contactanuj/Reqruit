// BottomNav.test.tsx — FE-2.2 (AC: #1, #3)

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { BottomNav } from "./BottomNav";
import { useLayoutStore } from "@/features/shell/store/layout-store";
import { useOnboardingStore } from "@/features/onboarding/store/onboarding-store";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/dashboard",
}));

beforeEach(() => {
  useLayoutStore.setState({
    sidebarCollapsed: false,
    copilotVisible: true,
    shortcutsOverlayVisible: false,
  });
  // Enable all features so nav items render as active links (not locked divs)
  useOnboardingStore.setState({
    onboardingComplete: true,
    goal: "find_jobs",
    showAllFeatures: true,
    unlockedFeatures: {},
  });
});

describe("BottomNav", () => {
  it("renders all five tabs", () => {
    render(<BottomNav />);
    expect(screen.getByRole("link", { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /jobs/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /applications/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /copilot/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /profile/i })).toBeInTheDocument();
  });

  it("marks active tab with aria-current=page", () => {
    render(<BottomNav />);
    const dashLink = screen.getByRole("link", { name: /dashboard/i });
    expect(dashLink).toHaveAttribute("aria-current", "page");
  });

  it("tab elements meet minimum 44px touch target (min-h-[44px])", () => {
    render(<BottomNav />);
    const dashLink = screen.getByRole("link", { name: /dashboard/i });
    // Class-based verification: check className contains min-h-[44px]
    expect(dashLink.className).toContain("min-h-[44px]");
  });

  it("has accessible nav landmark", () => {
    render(<BottomNav />);
    expect(
      screen.getByRole("navigation", { name: /mobile bottom navigation/i }),
    ).toBeInTheDocument();
  });
});
