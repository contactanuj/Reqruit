// types.ts — Interview feature types (FE-11.1 through FE-11.5)

// ---------------------------------------------------------------------------
// STAR Stories (FE-11.1)
// ---------------------------------------------------------------------------

export interface StarStory {
  id: string;
  title: string;
  situation: string;
  task: string;
  action: string;
  result: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface StarStoryFormData {
  title: string;
  situation: string;
  task: string;
  action: string;
  result: string;
  tags: string[];
}

// ---------------------------------------------------------------------------
// Interview Questions (FE-11.2)
// ---------------------------------------------------------------------------

export interface InterviewQuestion {
  id: string;
  text: string;
  difficulty: "easy" | "medium" | "hard";
  linked_star_story_ids: string[];
}

// ---------------------------------------------------------------------------
// Coaching (FE-11.3)
// ---------------------------------------------------------------------------

export interface CoachingFeedback {
  strengths: string;
  areasToImprove: string;
  reframeSuggestion: string;
}

// ---------------------------------------------------------------------------
// Mock Interview (FE-11.4)
// ---------------------------------------------------------------------------

export type InterviewType = "behavioral" | "technical" | "system_design";
export type SessionDuration = 30 | 45 | 60;

export interface MockSessionConfig {
  type: InterviewType;
  duration: SessionDuration;
}

export interface MockSession {
  id: string;
  config: MockSessionConfig;
  status: "active" | "complete";
  started_at: string;
  completed_at?: string;
}

// ---------------------------------------------------------------------------
// Transcript & Ratings (FE-11.5)
// ---------------------------------------------------------------------------

export interface TranscriptEntry {
  questionText: string;
  answerText: string;
  questionIndex: number;
}

export interface DimensionRating {
  dimension: "communication" | "depth" | "structure";
  score: number;
}

export interface TranscriptData {
  entries: TranscriptEntry[];
  overallScore: number;
  dimensions: DimensionRating[];
  recommendations: string[];
}

export interface SessionSummary {
  id: string;
  date: string;
  type: InterviewType;
  duration: SessionDuration;
  overallScore: number;
}
