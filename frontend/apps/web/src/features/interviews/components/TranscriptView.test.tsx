// TranscriptView.test.tsx — FE-11.5 co-located tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TranscriptView } from "./TranscriptView";
import type { TranscriptData } from "../types";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockUseTranscriptQuery = vi.fn();

vi.mock("../hooks/useTranscript", () => ({
  useTranscriptQuery: (...args: unknown[]) => mockUseTranscriptQuery(...args),
}));

// DOMPurify mock — tracks calls and returns cleaned string
const sanitizeSpy = vi.fn((input: string) => `sanitized:${input}`);
vi.mock("dompurify", () => ({
  default: { sanitize: (input: string) => sanitizeSpy(input) },
}));

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const MOCK_TRANSCRIPT: TranscriptData = {
  overallScore: 85,
  dimensions: [
    { dimension: "communication", score: 90 },
    { dimension: "depth", score: 72 },
    { dimension: "structure", score: 55 },
  ],
  entries: [
    {
      questionIndex: 0,
      questionText: "Tell me about a leadership challenge.",
      answerText: "I led a team of five engineers to deliver a critical project.",
    },
    {
      questionIndex: 1,
      questionText: "Describe a technical trade-off you made.",
      answerText: "We chose eventual consistency to reduce latency by 40%.",
    },
  ],
  recommendations: [
    "Provide more specific metrics in answers",
    "Improve structure using STAR format",
  ],
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("TranscriptView (FE-11.5)", () => {
  // 1. Shows loading state
  it("shows loading state when data is loading", () => {
    mockUseTranscriptQuery.mockReturnValue({ data: undefined, isLoading: true });

    render(<TranscriptView sessionId="sess-1" />);

    expect(screen.getByTestId("loading-state")).toBeInTheDocument();
    expect(screen.getByTestId("loading-state")).toHaveTextContent("Loading transcript");
  });

  // 2. Renders overall score
  it("renders overall score with correct value and green color", () => {
    mockUseTranscriptQuery.mockReturnValue({ data: MOCK_TRANSCRIPT, isLoading: false });

    render(<TranscriptView sessionId="sess-1" />);

    const scoreEl = screen.getByTestId("overall-score");
    expect(scoreEl).toHaveTextContent("85");
    expect(scoreEl.className).toContain("text-green-600");
  });

  it("renders overall score with amber color when between 60-79", () => {
    mockUseTranscriptQuery.mockReturnValue({
      data: { ...MOCK_TRANSCRIPT, overallScore: 65 },
      isLoading: false,
    });

    render(<TranscriptView sessionId="sess-1" />);

    const scoreEl = screen.getByTestId("overall-score");
    expect(scoreEl).toHaveTextContent("65");
    expect(scoreEl.className).toContain("text-amber-600");
  });

  it("renders overall score with red color when below 60", () => {
    mockUseTranscriptQuery.mockReturnValue({
      data: { ...MOCK_TRANSCRIPT, overallScore: 42 },
      isLoading: false,
    });

    render(<TranscriptView sessionId="sess-1" />);

    const scoreEl = screen.getByTestId("overall-score");
    expect(scoreEl).toHaveTextContent("42");
    expect(scoreEl.className).toContain("text-red-600");
  });

  // 3. Renders dimension bars with correct values
  it("renders dimension bars with correct scores", () => {
    mockUseTranscriptQuery.mockReturnValue({ data: MOCK_TRANSCRIPT, isLoading: false });

    render(<TranscriptView sessionId="sess-1" />);

    const commEl = screen.getByTestId("dimension-communication");
    expect(commEl).toBeInTheDocument();
    expect(commEl).toHaveTextContent("Communication");
    expect(commEl).toHaveTextContent("90");

    const depthEl = screen.getByTestId("dimension-depth");
    expect(depthEl).toBeInTheDocument();
    expect(depthEl).toHaveTextContent("Depth");
    expect(depthEl).toHaveTextContent("72");

    const structEl = screen.getByTestId("dimension-structure");
    expect(structEl).toBeInTheDocument();
    expect(structEl).toHaveTextContent("Structure");
    expect(structEl).toHaveTextContent("55");
  });

  // 4. Renders transcript entries
  it("renders transcript entries in collapsed state", () => {
    mockUseTranscriptQuery.mockReturnValue({ data: MOCK_TRANSCRIPT, isLoading: false });

    render(<TranscriptView sessionId="sess-1" />);

    expect(screen.getByTestId("transcript-entry-0")).toBeInTheDocument();
    expect(screen.getByTestId("transcript-entry-1")).toBeInTheDocument();
    // Questions visible (sanitized)
    expect(screen.getByText(/sanitized:Tell me about a leadership challenge/)).toBeInTheDocument();
    expect(screen.getByText(/sanitized:Describe a technical trade-off/)).toBeInTheDocument();
    // Answers not visible (collapsed)
    expect(screen.queryByText(/sanitized:I led a team/)).not.toBeInTheDocument();
  });

  // 5. Expanding entry shows answer
  it("expanding an entry shows the answer text", async () => {
    mockUseTranscriptQuery.mockReturnValue({ data: MOCK_TRANSCRIPT, isLoading: false });
    const user = userEvent.setup();

    render(<TranscriptView sessionId="sess-1" />);

    // Click the first entry to expand
    const firstEntry = screen.getByTestId("transcript-entry-0");
    const expandButton = firstEntry.querySelector("button")!;
    await user.click(expandButton);

    // Answer should now be visible
    expect(screen.getByText(/sanitized:I led a team of five engineers/)).toBeInTheDocument();

    // Click again to collapse
    await user.click(expandButton);
    expect(screen.queryByText(/sanitized:I led a team of five engineers/)).not.toBeInTheDocument();
  });

  // 6. Renders recommendations
  it("renders recommendations list", () => {
    mockUseTranscriptQuery.mockReturnValue({ data: MOCK_TRANSCRIPT, isLoading: false });

    render(<TranscriptView sessionId="sess-1" />);

    const recList = screen.getByTestId("recommendations-list");
    expect(recList).toBeInTheDocument();
    expect(recList.querySelectorAll("li")).toHaveLength(2);
    expect(screen.getByText(/sanitized:Provide more specific metrics/)).toBeInTheDocument();
    expect(screen.getByText(/sanitized:Improve structure using STAR/)).toBeInTheDocument();
  });

  // 7. DOMPurify sanitizes content
  it("passes AI text through DOMPurify.sanitize", () => {
    mockUseTranscriptQuery.mockReturnValue({ data: MOCK_TRANSCRIPT, isLoading: false });

    render(<TranscriptView sessionId="sess-1" />);

    // Question texts should be sanitized
    expect(sanitizeSpy).toHaveBeenCalledWith("Tell me about a leadership challenge.");
    expect(sanitizeSpy).toHaveBeenCalledWith("Describe a technical trade-off you made.");
    // Recommendations should be sanitized
    expect(sanitizeSpy).toHaveBeenCalledWith("Provide more specific metrics in answers");
    expect(sanitizeSpy).toHaveBeenCalledWith("Improve structure using STAR format");
  });
});
