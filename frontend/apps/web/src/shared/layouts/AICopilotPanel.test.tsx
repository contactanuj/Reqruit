// AICopilotPanel.test.tsx — FE-2.6 (AC: #1, #3)
// Note: persona by route is tested more thoroughly in use-copilot-context.test.ts

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { AICopilotPanel } from "./AICopilotPanel";
import { useLayoutStore } from "@/features/shell/store/layout-store";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/jobs",
}));

vi.mock("@repo/ui/hooks", () => ({
  useSSEStream: () => ({
    state: { status: "idle" },
    cancel: vi.fn(),
    retry: vi.fn(),
  }),
  useKeyboardShortcuts: vi.fn(),
}));

beforeEach(() => {
  useLayoutStore.setState({
    sidebarCollapsed: false,
    copilotVisible: true,
    shortcutsOverlayVisible: false,
  });
});

describe("AICopilotPanel", () => {
  it("renders with Company Research Analyst persona on /jobs route", () => {
    render(<AICopilotPanel />);
    // Heading element specifically (h2)
    expect(screen.getByRole("heading", { name: "Company Research Analyst" })).toBeInTheDocument();
  });

  it("renders the AI Copilot panel landmark", () => {
    render(<AICopilotPanel />);
    // aside has implicit role=complementary; query by test-id for reliability
    expect(screen.getByTestId("copilot-panel")).toBeInTheDocument();
  });

  it("shows message input with correct aria-label", () => {
    render(<AICopilotPanel />);
    expect(
      screen.getByRole("textbox", { name: /message ai copilot/i }),
    ).toBeInTheDocument();
  });

  it("returns null when copilotVisible is false", () => {
    useLayoutStore.setState({ copilotVisible: false });
    const { container } = render(<AICopilotPanel />);
    expect(container.firstChild).toBeNull();
  });

  it("shows pre-loaded prompt chip when no messages", () => {
    render(<AICopilotPanel />);
    // The pre-prompt chip appears as a button
    const chipBtn = screen.getByRole("button", { name: /help me research/i });
    expect(chipBtn).toBeInTheDocument();
  });
});
