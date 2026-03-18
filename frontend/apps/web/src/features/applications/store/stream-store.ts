// stream-store.ts — Zustand store for SSE streaming state
// Rule 9: ALL streaming state lives here — NEVER in local component useState.
// One store for all 5 SSE workflows: cover letter, outreach, interview coaching,
// negotiation advisor, career plan.

import { create } from "zustand";
import type { HITLDraft } from "@repo/types";

interface StreamState {
  /** Thread ID of the currently active SSE stream (null when idle). */
  activeThreadId: string | null;
  /** Human-readable milestone label from the last `pipeline_step` event. */
  milestoneLabel: string | null;
  /** Accumulated streaming text buffer — appended token-by-token. */
  streamingBuffer: string;
  /** True once the `complete` SSE event has been received. */
  isComplete: boolean;
  /** HITL draft returned by `hitl_ready` SSE event — null until ready. */
  hitlDraft: HITLDraft | null;
}

interface StreamActions {
  /** Append a streaming token to the buffer. */
  appendToken: (token: string) => void;
  /** Update the milestone label shown in the pipeline visualizer. */
  setMilestone: (label: string | null) => void;
  /** Mark stream as complete for non-HITL flows. */
  setComplete: () => void;
  /** Store the HITL draft when the backend is ready for human review. */
  setHITL: (draft: HITLDraft) => void;
  /** Set the active thread ID when a generation job starts. */
  setActiveThread: (threadId: string | null) => void;
  /** Reset all stream state — call before starting a new generation. */
  reset: () => void;
}

const initialState: StreamState = {
  activeThreadId: null,
  milestoneLabel: null,
  streamingBuffer: "",
  isComplete: false,
  hitlDraft: null,
};

export const useStreamStore = create<StreamState & StreamActions>((set) => ({
  ...initialState,

  appendToken: (token) =>
    set((state) => ({ streamingBuffer: state.streamingBuffer + token })),

  setMilestone: (label) => set({ milestoneLabel: label }),

  setComplete: () => set({ isComplete: true }),

  setHITL: (draft) => set({ hitlDraft: draft, isComplete: true }),

  setActiveThread: (threadId) => set({ activeThreadId: threadId }),

  reset: () => set(initialState),
}));
