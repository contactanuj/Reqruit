// HITLReviewPanel — Human-in-the-Loop review split-screen (FE-7.3)
// Shared component used by cover letter, outreach, negotiation.
// DEV NOTE: ResizablePanelGroup not available in this project —
//           using CSS flex split with responsive layout instead.

import * as React from "react";
import { DraftPane } from "./DraftPane";
import { SourcePane } from "./SourcePane";
import { ActionBar } from "./ActionBar";

export interface HITLReviewPanelProps {
  /** AI-generated draft content */
  draftContent: string;
  /** Original source document (job description, etc.) */
  sourceContent: string;
  /** Source pane title (defaults to "Job Description") */
  sourceTitle?: string;
  /** Called when user approves */
  onApprove: () => void;
  /** Called when user requests revision with feedback */
  onRevise: (feedback: string) => void;
  /** Whether approve is in progress */
  isApproving?: boolean;
  /** Whether revise is in progress */
  isRevising?: boolean;
}

export function HITLReviewPanel({
  draftContent,
  sourceContent,
  sourceTitle,
  onApprove,
  onRevise,
  isApproving = false,
  isRevising = false,
}: HITLReviewPanelProps) {
  const [isEditing, setIsEditing] = React.useState(false);
  const [showReviseInput, setShowReviseInput] = React.useState(false);
  const [feedback, setFeedback] = React.useState("");
  const draftRef = React.useRef<HTMLDivElement>(null);

  // Focus draft pane on mount (AC #4)
  React.useEffect(() => {
    draftRef.current?.focus();
  }, []);

  const handleReviseClick = () => {
    setShowReviseInput(true);
  };

  const handleReviseSubmit = () => {
    if (!feedback.trim()) return;
    onRevise(feedback.trim());
    setFeedback("");
    setShowReviseInput(false);
  };

  return (
    <div
      className="flex h-full flex-col"
      data-testid="hitl-review-panel"
    >
      {/* Split panels */}
      {/* TODO: Replace flex split with ResizablePanelGroup from @radix-ui when available
         for proper drag-to-resize. Currently using CSS resize on desktop as a lightweight
         alternative. */}
      <div className="flex flex-1 flex-col overflow-hidden md:flex-row">
        {/* Left: Draft pane — CSS resize handle on desktop */}
        <div
          ref={draftRef}
          tabIndex={-1}
          className="flex-1 overflow-hidden border-b border-border outline-none md:border-b-0 md:border-r md:resize-x md:overflow-auto md:min-w-[200px] md:max-w-[80%]"
          data-testid="draft-panel"
        >
          <DraftPane
            content={draftContent}
            isEditable={isEditing}
          />
        </div>

        {/* Right: Source pane (read-only) */}
        <div
          className="flex-1 overflow-hidden min-w-[200px]"
          data-testid="source-panel"
        >
          <SourcePane
            content={sourceContent}
            title={sourceTitle}
          />
        </div>
      </div>

      {/* Revision feedback input */}
      {showReviseInput && (
        <div
          className="border-t border-border bg-background p-4"
          data-testid="revise-feedback-area"
        >
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Tell me how to improve it…"
            rows={3}
            className="w-full resize-none rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            data-testid="feedback-textarea"
            aria-label="Revision feedback"
          />
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={handleReviseSubmit}
              disabled={!feedback.trim() || isRevising}
              className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              data-testid="submit-feedback-button"
            >
              {isRevising ? "Submitting…" : "Submit Feedback"}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowReviseInput(false);
                setFeedback("");
              }}
              className="rounded-md border border-border px-4 py-2 text-sm hover:bg-muted"
              data-testid="cancel-feedback-button"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Action bar — pinned above keyboard */}
      <ActionBar
        onApprove={onApprove}
        onRevise={handleReviseClick}
        onToggleEdit={() => setIsEditing((v) => !v)}
        isEditing={isEditing}
        isApproving={isApproving}
        isRevising={isRevising}
      />
    </div>
  );
}

export { DraftPane } from "./DraftPane";
export { SourcePane } from "./SourcePane";
export { ActionBar } from "./ActionBar";
