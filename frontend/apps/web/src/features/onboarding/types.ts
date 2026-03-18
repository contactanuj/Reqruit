// Onboarding feature types (FE-3.1)

export type OnboardingGoal =
  | "find_jobs"
  | "interview_prep"
  | "negotiate_offer"
  | "track_applications";

export interface GoalOption {
  id: OnboardingGoal;
  label: string;
  description: string;
  /** Features visible when this goal is selected */
  features: FeatureKey[];
}

export type FeatureKey =
  | "dashboard"
  | "jobs"
  | "applications"
  | "interviews"
  | "offers"
  | "career"
  | "profile";

export const GOAL_OPTIONS: GoalOption[] = [
  {
    id: "find_jobs",
    label: "Find jobs",
    description: "Discover and save relevant job postings",
    features: ["dashboard", "jobs", "applications", "profile"],
  },
  {
    id: "interview_prep",
    label: "Interview prep",
    description: "Prepare for upcoming interviews",
    features: ["dashboard", "interviews", "jobs", "applications"],
  },
  {
    id: "negotiate_offer",
    label: "Negotiate offer",
    description: "Evaluate and negotiate job offers",
    features: ["dashboard", "offers"],
  },
  {
    id: "track_applications",
    label: "Track applications",
    description: "Monitor your application pipeline",
    features: ["dashboard", "applications", "jobs"],
  },
];

export interface OnboardingPayload {
  goal: OnboardingGoal;
  onboarding_complete: boolean;
}

export interface UpdateSettingsPayload {
  show_all_features: boolean;
}
