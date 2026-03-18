// Career types for FE-13

export interface OnboardingMilestone {
  id: string;
  text: string;
  completed: boolean;
  phase: "days_1_30" | "days_31_60" | "days_61_90";
}

export interface OnboardingPlan {
  id: string;
  roleTitle: string;
  company: string;
  startDate: string;
  milestones: OnboardingMilestone[];
  createdAt: string;
}

export type MoodLevel = 1 | 2 | 3 | 4 | 5;

export interface WellnessCheckIn {
  id: string;
  date: string;
  mood: MoodLevel;
  energy: MoodLevel;
}

export interface BurnoutRisk {
  score: number; // 0-100
  trend: { date: string; score: number }[];
}

export interface WellnessTrend {
  data: { date: string; mood: number; energy: number }[];
}

export interface SkillMilestone {
  skill: string;
  estimatedMonths: number;
}

export interface PathProjection {
  roleTitle: string;
  transitionMonths: number;
  milestones: SkillMilestone[];
  resources: string[];
}
