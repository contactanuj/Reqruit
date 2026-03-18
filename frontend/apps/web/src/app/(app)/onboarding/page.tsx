// Onboarding page — goal selection (FE-3.1)
// Only shown when onboarding_complete = false.

import { OnboardingFlow } from "@/features/onboarding/components/OnboardingFlow";

export default function OnboardingPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background">
      <OnboardingFlow />
    </main>
  );
}
