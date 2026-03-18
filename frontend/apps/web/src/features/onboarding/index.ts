// Onboarding feature public API (FE-3.1, FE-3.2, FE-3.3, FE-3.4)
// Cross-feature imports must use this index (Rule 8: no deep imports)

export { useOnboardingStore } from "./store/onboarding-store";
export type { OnboardingStore } from "./store/onboarding-store";

export { useProgressiveDisclosure, getUnlockFromStatusTransition } from "./hooks/useProgressiveDisclosure";
export type { FeatureVisibility } from "./hooks/useProgressiveDisclosure";

export { useSetGoal, useUpdateSettings } from "./hooks/useOnboarding";

export { GoalSelector } from "./components/GoalSelector";
export { OnboardingFlow } from "./components/OnboardingFlow";
export { GeneralSettingsForm } from "./components/GeneralSettingsForm";
export { GoalChangeSection } from "./components/GoalChangeSection";

export type { OnboardingGoal, FeatureKey, GoalOption } from "./types";
export { GOAL_OPTIONS } from "./types";
