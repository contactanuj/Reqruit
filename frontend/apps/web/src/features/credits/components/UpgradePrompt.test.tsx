import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { UpgradePrompt } from "./UpgradePrompt";
import { useCreditsStore } from "../store/credits-store";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

describe("UpgradePrompt", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders when credits <= 1", () => {
    useCreditsStore.setState({ dailyCredits: 1 });
    render(<UpgradePrompt />);
    expect(screen.getByTestId("upgrade-prompt")).toBeInTheDocument();
  });

  it("renders when credits = 0", () => {
    useCreditsStore.setState({ dailyCredits: 0 });
    render(<UpgradePrompt />);
    expect(screen.getByText("You've used all your daily credits")).toBeInTheDocument();
  });

  it("does not render when credits > 1", () => {
    useCreditsStore.setState({ dailyCredits: 5 });
    render(<UpgradePrompt />);
    expect(screen.queryByTestId("upgrade-prompt")).not.toBeInTheDocument();
  });

  it("Upgrade CTA navigates to pricing/upgrade page", () => {
    useCreditsStore.setState({ dailyCredits: 0 });
    render(<UpgradePrompt />);
    fireEvent.click(screen.getByTestId("upgrade-cta"));
    expect(mockPush).toHaveBeenCalledWith("/settings/upgrade");
  });

  it("shows list of AI actions with credit costs", () => {
    useCreditsStore.setState({ dailyCredits: 1 });
    render(<UpgradePrompt />);
    expect(screen.getByText("Generate cover letter")).toBeInTheDocument();
    expect(screen.getByText("Interview prep")).toBeInTheDocument();
  });

  it("has role=alert for screen reader announcement", () => {
    useCreditsStore.setState({ dailyCredits: 0 });
    render(<UpgradePrompt />);
    const prompt = screen.getByRole("alert");
    expect(prompt).toBeInTheDocument();
  });
});
