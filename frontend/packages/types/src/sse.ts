/** A single step in the AI pipeline visualizer. */
export interface PipelineStep {
  id: string;
  label: string;
  status: "pending" | "active" | "complete" | "error";
  startedAt?: number;
  completedAt?: number;
}

/**
 * Discriminated union of all SSE stream states.
 * Exposed by useSSEStream hook.
 */
export type SSEStreamState =
  | { status: "idle" }
  | { status: "connecting" }
  | { status: "streaming"; steps: PipelineStep[]; partialText: string }
  | { status: "complete"; steps: PipelineStep[]; finalText: string }
  | { status: "hitl_ready"; steps: PipelineStep[]; partialText: string; hitlDraft: HITLDraft }
  | { status: "error"; error: string; retryCount: number };

/**
 * Human-in-the-loop draft returned by the `hitl_ready` SSE event.
 * Shared across cover letter, outreach, interview coaching, negotiation, career plan.
 */
export interface HITLDraft {
  content: string;
  threadId: string;
  generationType:
    | "cover_letter"
    | "outreach"
    | "interview_coaching"
    | "negotiation"
    | "career_plan";
}

/** Structured SSE error payload (subset of FastAPI error shape). */
export interface SSEError {
  code: string;
  message: string;
  retryable: boolean;
}

/**
 * Labels shown in the AI pipeline milestone visualizer.
 * Synced from backend `node_complete` events.
 */
export type MilestoneLabel =
  | "Analyzing job requirements"
  | "Researching company"
  | "Drafting content"
  | "Refining tone"
  | "Finalizing";
