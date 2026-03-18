// career feature barrel export (FE-13)

// Components
export { OnboardingPlanGenerator } from "./components/OnboardingPlanGenerator";
export { OnboardingPlanView } from "./components/OnboardingPlanView";
export { WellnessCheckIn } from "./components/WellnessCheckIn";
export { BurnoutGauge } from "./components/BurnoutGauge";
export { WellnessTrendChart } from "./components/WellnessTrendChart";
export { PathPlanner } from "./components/PathPlanner";
export { ProjectionCard } from "./components/ProjectionCard";

// Hooks
export { useOnboardingPlanMutation, useToggleMilestone } from "./hooks/useOnboardingPlan";
export { useWellnessCheckIn, useBurnoutRisk, useWellnessTrend } from "./hooks/useWellness";
export { useGenerateProjections } from "./hooks/usePathProjections";

// Types
export type {
  OnboardingMilestone,
  OnboardingPlan,
  MoodLevel,
  WellnessCheckIn as WellnessCheckInType,
  BurnoutRisk,
  WellnessTrend,
  SkillMilestone,
  PathProjection,
} from "./types";
