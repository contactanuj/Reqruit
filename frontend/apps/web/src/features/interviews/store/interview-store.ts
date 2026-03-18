// interview-store.ts — Zustand store for mock interview session state (FE-11.4)

import { create } from "zustand";
import type { MockSessionConfig, InterviewType, SessionDuration } from "../types";

interface InterviewState {
  activeSessionId: string | null;
  currentQuestionIndex: number;
  totalQuestions: number;
  answers: string[];
  sessionConfig: MockSessionConfig;
  sessionStatus: "idle" | "active" | "complete";
  startedAt: number | null;
}

interface InterviewActions {
  startSession: (sessionId: string, config: MockSessionConfig) => void;
  recordAnswer: (answer: string) => void;
  advanceQuestion: () => void;
  setTotalQuestions: (count: number) => void;
  endSession: () => void;
  resetSession: () => void;
}

const initialState: InterviewState = {
  activeSessionId: null,
  currentQuestionIndex: 0,
  totalQuestions: 0,
  answers: [],
  sessionConfig: { type: "behavioral" as InterviewType, duration: 30 as SessionDuration },
  sessionStatus: "idle",
  startedAt: null,
};

export const useInterviewStore = create<InterviewState & InterviewActions>((set) => ({
  ...initialState,

  startSession: (sessionId, config) =>
    set({
      activeSessionId: sessionId,
      sessionConfig: config,
      sessionStatus: "active",
      currentQuestionIndex: 0,
      answers: [],
      startedAt: Date.now(),
    }),

  recordAnswer: (answer) =>
    set((state) => ({ answers: [...state.answers, answer] })),

  advanceQuestion: () =>
    set((state) => {
      const nextIndex = state.currentQuestionIndex + 1;
      if (nextIndex >= state.totalQuestions) {
        return { currentQuestionIndex: nextIndex, sessionStatus: "complete" };
      }
      return { currentQuestionIndex: nextIndex };
    }),

  setTotalQuestions: (count) => set({ totalQuestions: count }),

  endSession: () => set({ sessionStatus: "complete" }),

  resetSession: () => set(initialState),
}));
