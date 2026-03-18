// NegotiationSession.test.tsx — FE-12.4 co-located tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { NegotiationSession } from "./NegotiationSession";
import type { NegotiationSections } from "../types";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

let mockHitlDraft: { content: string } | null = null;

vi.mock("@/features/applications/store/stream-store", () => {
  const store = (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ hitlDraft: mockHitlDraft });
  store.getState = () => ({ hitlDraft: mockHitlDraft });
  store.setState = vi.fn();
  return { useStreamStore: store };
});

const mockOnApproveEmail = vi.fn();
const mockOnReviseEmail = vi.fn();
const mockOnReset = vi.fn();

// Mock HITLReviewPanel as a simple div with buttons
vi.mock("@repo/ui/components/HITLReviewPanel", () => ({
  HITLReviewPanel: ({
    draftContent,
    onApprove,
    onRevise,
  }: {
    draftContent: string;
    onApprove: () => void;
    onRevise: (feedback: string) => void;
    sourceContent: string;
    sourceTitle: string;
    isApproving?: boolean;
    isRevising?: boolean;
  }) => (
    <div data-testid="mock-hitl-panel">
      <div data-testid="hitl-draft-content">{draftContent}</div>
      <button data-testid="hitl-approve-button" onClick={onApprove}>
        Approve
      </button>
      <button
        data-testid="hitl-revise-button"
        onClick={() => onRevise("Make it more formal")}
      >
        Revise
      </button>
    </div>
  ),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const emptySections: NegotiationSections = {
  strategy: "",
  conversationScript: "",
  emailDraft: "",
};

const fullSections: NegotiationSections = {
  strategy: "Start by expressing enthusiasm for the role.",
  conversationScript: "You: Thank you for the offer. I'd like to discuss compensation...",
  emailDraft: "Dear Hiring Manager,\n\nThank you for extending this offer...",
};

interface RenderProps {
  sections?: NegotiationSections;
  isStreaming?: boolean;
  isComplete?: boolean;
}

function renderSession(props: RenderProps = {}) {
  return render(
    <NegotiationSession
      sections={props.sections ?? emptySections}
      isStreaming={props.isStreaming ?? false}
      isComplete={props.isComplete ?? false}
      offerId="offer-1"
      onApproveEmail={mockOnApproveEmail}
      onReviseEmail={mockOnReviseEmail}
      onReset={mockOnReset}
    />,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("NegotiationSession (FE-12.4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockHitlDraft = null;
  });

  it("renders the session container", () => {
    renderSession();
    expect(screen.getByTestId("negotiation-session")).toBeInTheDocument();
  });

  it("shows streaming indicator when isStreaming is true", () => {
    renderSession({ isStreaming: true });

    expect(screen.getByTestId("negotiation-streaming")).toBeInTheDocument();
    expect(screen.getByText("Generating negotiation strategy...")).toBeInTheDocument();
  });

  it("does not show streaming indicator when not streaming", () => {
    renderSession({ isStreaming: false });

    expect(screen.queryByTestId("negotiation-streaming")).not.toBeInTheDocument();
  });

  it("renders strategy section when available", () => {
    renderSession({
      isStreaming: true,
      sections: { ...emptySections, strategy: "Be confident." },
    });

    expect(screen.getByTestId("section-strategy")).toBeInTheDocument();
    expect(screen.getByText("Strategy")).toBeInTheDocument();
  });

  it("renders conversation script section when available", () => {
    renderSession({
      isStreaming: true,
      sections: {
        ...emptySections,
        strategy: "Strategy text",
        conversationScript: "Script text",
      },
    });

    expect(screen.getByTestId("section-conversation-script")).toBeInTheDocument();
  });

  it("renders email draft section during streaming (no HITL)", () => {
    renderSession({
      isStreaming: true,
      sections: fullSections,
    });

    // During streaming, email draft shows as plain text (not HITL)
    expect(screen.getByTestId("section-email-draft")).toBeInTheDocument();
    expect(screen.queryByTestId("email-hitl-review")).not.toBeInTheDocument();
  });

  it("shows HITL review panel for email draft when complete", () => {
    mockHitlDraft = { content: "Revised email content" };
    renderSession({
      isComplete: true,
      sections: fullSections,
    });

    expect(screen.getByTestId("email-hitl-review")).toBeInTheDocument();
    expect(screen.getByTestId("mock-hitl-panel")).toBeInTheDocument();
    // Plain email draft section should NOT be shown
    expect(screen.queryByTestId("section-email-draft")).not.toBeInTheDocument();
  });

  it("calls onApproveEmail when HITL approve is clicked", async () => {
    mockHitlDraft = { content: "Email content" };
    const user = userEvent.setup();
    renderSession({ isComplete: true, sections: fullSections });

    await user.click(screen.getByTestId("hitl-approve-button"));

    expect(mockOnApproveEmail).toHaveBeenCalledOnce();
  });

  it("calls onReviseEmail when HITL revise is clicked", async () => {
    mockHitlDraft = { content: "Email content" };
    const user = userEvent.setup();
    renderSession({ isComplete: true, sections: fullSections });

    await user.click(screen.getByTestId("hitl-revise-button"));

    expect(mockOnReviseEmail).toHaveBeenCalledWith("Make it more formal");
  });

  it("shows reset button when complete with sections", () => {
    renderSession({ isComplete: true, sections: fullSections });

    expect(screen.getByTestId("reset-negotiation-button")).toBeInTheDocument();
    expect(screen.getByTestId("reset-negotiation-button")).toHaveTextContent(
      "Start new negotiation",
    );
  });

  it("calls onReset when reset button is clicked", async () => {
    const user = userEvent.setup();
    renderSession({ isComplete: true, sections: fullSections });

    await user.click(screen.getByTestId("reset-negotiation-button"));

    expect(mockOnReset).toHaveBeenCalledOnce();
  });

  it("has aria-live on streaming indicator", () => {
    renderSession({ isStreaming: true });

    expect(screen.getByTestId("negotiation-streaming")).toHaveAttribute(
      "aria-live",
      "polite",
    );
  });

  it("does not show reset button when streaming", () => {
    renderSession({ isStreaming: true, sections: fullSections });

    expect(screen.queryByTestId("reset-negotiation-button")).not.toBeInTheDocument();
  });
});
