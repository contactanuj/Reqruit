// interviews feature barrel export (FE-11)

// Components
export { StarStoryList } from "./components/StarStoryList";
export { StarStoryForm } from "./components/StarStoryForm";
export { InterviewQuestions } from "./components/InterviewQuestions";
export { CoachingPanel } from "./components/CoachingPanel";
export { MockInterviewSetup } from "./components/MockInterviewSetup";
export { MockInterviewSession } from "./components/MockInterviewSession";
export { TranscriptView } from "./components/TranscriptView";
export { SessionHistory } from "./components/SessionHistory";

// Hooks
export { useStarStoriesQuery, useCreateStarStory, useUpdateStarStory, useDeleteStarStory } from "./hooks/useStarStories";
export { useInterviewQuestionsQuery, useGenerateQuestions } from "./hooks/useInterviewQuestions";
export { useInterviewCoaching } from "./hooks/useInterviewCoaching";
export { useStartSession, useSubmitAnswer } from "./hooks/useMockInterview";
export { useTranscriptQuery } from "./hooks/useTranscript";
export { useSessionHistoryQuery } from "./hooks/useSessionHistory";

// Store
export { useInterviewStore } from "./store/interview-store";

// Types
export type {
  StarStory,
  StarStoryFormData,
  InterviewQuestion,
  CoachingFeedback,
  InterviewType,
  SessionDuration,
  MockSessionConfig,
  MockSession,
  TranscriptEntry,
  DimensionRating,
  TranscriptData,
  SessionSummary,
} from "./types";
