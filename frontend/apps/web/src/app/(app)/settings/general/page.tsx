// Settings → General page (FE-3.4)
// Contains "Show all features" toggle and goal selection.

import { GeneralSettingsForm } from "@/features/onboarding/components/GeneralSettingsForm";
import { GoalChangeSection } from "@/features/onboarding/components/GoalChangeSection";

export default function GeneralSettingsPage() {
  return (
    <main className="flex flex-col gap-8">
      <h1 className="text-xl font-bold">General settings</h1>
      <GoalChangeSection />
      <GeneralSettingsForm />
    </main>
  );
}
