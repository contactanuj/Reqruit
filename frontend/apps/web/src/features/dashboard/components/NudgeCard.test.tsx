import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NudgeCard } from "./NudgeCard";
import { NudgeCardList } from "./NudgeCardList";
import type { Nudge } from "../hooks/useDashboard";

// Mock the hooks for NudgeCardList
vi.mock("../hooks/useDashboard", async (importOriginal) => {
  const original = await importOriginal<typeof import("../hooks/useDashboard")>();
  return {
    ...original,
    useNudges: vi.fn(),
    useDismissNudge: vi.fn(),
  };
});

import { useNudges, useDismissNudge } from "../hooks/useDashboard";

const mockNudges: Nudge[] = [
  {
    id: "1",
    type: "follow_up",
    message: "Follow up with Acme — it's been 14 days since you applied",
    ctaLabel: "Follow up",
    ctaHref: "/jobs/1?tab=contacts",
  },
  {
    id: "2",
    type: "interview_prep",
    message: "Prepare for your interview at Google tomorrow",
    ctaLabel: "Prep now",
    ctaHref: "/applications/2",
  },
  {
    id: "3",
    type: "deadline",
    message: "Application deadline for Meta is in 2 days",
    ctaLabel: "Apply now",
    ctaHref: "/jobs/3",
  },
];

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("NudgeCard", () => {
  it("renders nudge message and CTA", () => {
    const onDismiss = vi.fn();
    render(
      <NudgeCard nudge={mockNudges[0]} onDismiss={onDismiss} />,
      { wrapper }
    );

    expect(
      screen.getByText("Follow up with Acme — it's been 14 days since you applied")
    ).toBeInTheDocument();
    expect(screen.getByText("Follow up")).toBeInTheDocument();
  });

  it("calls onDismiss when dismiss button clicked", () => {
    const onDismiss = vi.fn();
    render(
      <NudgeCard nudge={mockNudges[0]} onDismiss={onDismiss} />,
      { wrapper }
    );

    fireEvent.click(screen.getByLabelText("Dismiss nudge"));
    expect(onDismiss).toHaveBeenCalledWith("1");
  });
});

describe("NudgeCardList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows max 3 nudge cards", () => {
    const fourNudges: Nudge[] = [
      ...mockNudges,
      {
        id: "4",
        type: "ghost_job",
        message: "Check on job posting at Stripe — it may have been removed",
        ctaLabel: "Check",
        ctaHref: "/jobs/4",
      },
    ];

    vi.mocked(useNudges).mockReturnValue({
      data: fourNudges,
      isPending: false,
    } as ReturnType<typeof useNudges>);

    vi.mocked(useDismissNudge).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useDismissNudge>);

    render(<NudgeCardList />, { wrapper });

    // 3 visible nudge cards
    expect(screen.getByTestId("nudge-card-1")).toBeInTheDocument();
    expect(screen.getByTestId("nudge-card-2")).toBeInTheDocument();
    expect(screen.getByTestId("nudge-card-3")).toBeInTheDocument();
    expect(screen.queryByTestId("nudge-card-4")).not.toBeInTheDocument();

    // "See all nudges" link
    expect(screen.getByText("See all nudges")).toBeInTheDocument();
  });

  it("does not show 'See all' when 3 or fewer nudges", () => {
    vi.mocked(useNudges).mockReturnValue({
      data: mockNudges,
      isPending: false,
    } as ReturnType<typeof useNudges>);

    vi.mocked(useDismissNudge).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useDismissNudge>);

    render(<NudgeCardList />, { wrapper });

    expect(screen.queryByText("See all nudges")).not.toBeInTheDocument();
  });

  it("optimistically removes card on dismiss", () => {
    const mutateFn = vi.fn();
    vi.mocked(useNudges).mockReturnValue({
      data: mockNudges,
      isPending: false,
    } as ReturnType<typeof useNudges>);

    vi.mocked(useDismissNudge).mockReturnValue({
      mutate: mutateFn,
      isPending: false,
    } as unknown as ReturnType<typeof useDismissNudge>);

    render(<NudgeCardList />, { wrapper });

    const dismissBtn = screen.getAllByLabelText("Dismiss nudge")[0];
    fireEvent.click(dismissBtn);

    expect(mutateFn).toHaveBeenCalledWith("1");
  });
});
