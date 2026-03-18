import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MorningBriefingCard } from "./MorningBriefingCard";
import type { MorningBriefing } from "../hooks/useDashboard";

// Mock the hook
vi.mock("../hooks/useDashboard", async (importOriginal) => {
  const original = await importOriginal<typeof import("../hooks/useDashboard")>();
  return {
    ...original,
    useMorningBriefing: vi.fn(),
  };
});

import { useMorningBriefing } from "../hooks/useDashboard";

const mockBriefing: MorningBriefing = {
  newJobMatchCount: 5,
  streakDays: 7,
  pendingActions: [
    {
      id: "1",
      urgency: "deadline",
      description: "Submit application to Google by Friday",
      ctaLabel: "Submit",
      ctaHref: "/applications/1",
    },
    {
      id: "2",
      urgency: "interview",
      description: "Prepare for interview at Meta",
      ctaLabel: "Prepare",
      ctaHref: "/applications/2",
    },
    {
      id: "3",
      urgency: "document",
      description: "Upload cover letter for Amazon",
      ctaLabel: "Upload",
      ctaHref: "/applications/3",
    },
    {
      id: "4",
      urgency: "match",
      description: "New job match at Stripe",
      ctaLabel: "View",
      ctaHref: "/jobs/4",
    },
  ],
};

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("MorningBriefingCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders card with correct data sections", () => {
    vi.mocked(useMorningBriefing).mockReturnValue({
      data: mockBriefing,
      isPending: false,
      isError: false,
    } as ReturnType<typeof useMorningBriefing>);

    render(<MorningBriefingCard />, { wrapper });

    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("new jobs since your last visit")).toBeInTheDocument();
    expect(screen.getByText(/7/)).toBeInTheDocument();
    expect(screen.getByText(/day streak/)).toBeInTheDocument();
  });

  it("has role=region with aria-label='Morning briefing'", () => {
    vi.mocked(useMorningBriefing).mockReturnValue({
      data: mockBriefing,
      isPending: false,
      isError: false,
    } as ReturnType<typeof useMorningBriefing>);

    render(<MorningBriefingCard />, { wrapper });

    const region = screen.getByRole("region", { name: "Morning briefing" });
    expect(region).toBeInTheDocument();
  });

  it("renders pending actions using ul/li", () => {
    vi.mocked(useMorningBriefing).mockReturnValue({
      data: mockBriefing,
      isPending: false,
      isError: false,
    } as ReturnType<typeof useMorningBriefing>);

    render(<MorningBriefingCard />, { wrapper });

    const list = screen.getByRole("list");
    expect(list).toBeInTheDocument();
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(4);
  });

  it("shows skeleton while loading", () => {
    vi.mocked(useMorningBriefing).mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    } as ReturnType<typeof useMorningBriefing>);

    render(<MorningBriefingCard />, { wrapper });

    expect(screen.getByLabelText("Loading morning briefing")).toBeInTheDocument();
  });

  it("shows max 5 actions with 'See all' link when more exist", () => {
    const manyActions = Array.from({ length: 7 }, (_, i) => ({
      id: String(i),
      urgency: "match" as const,
      description: `Action ${i}`,
      ctaLabel: "View",
      ctaHref: `/jobs/${i}`,
    }));

    vi.mocked(useMorningBriefing).mockReturnValue({
      data: { ...mockBriefing, pendingActions: manyActions },
      isPending: false,
      isError: false,
    } as ReturnType<typeof useMorningBriefing>);

    render(<MorningBriefingCard />, { wrapper });

    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(5);
    expect(screen.getByText("See all actions")).toBeInTheDocument();
  });

  it("shows IST reset indicator", () => {
    vi.mocked(useMorningBriefing).mockReturnValue({
      data: mockBriefing,
      isPending: false,
      isError: false,
    } as ReturnType<typeof useMorningBriefing>);

    render(<MorningBriefingCard />, { wrapper });

    expect(screen.getByText("Resets at midnight IST")).toBeInTheDocument();
  });
});
