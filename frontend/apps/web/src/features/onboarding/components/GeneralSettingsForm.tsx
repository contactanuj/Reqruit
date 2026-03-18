"use client";

// GeneralSettingsForm.tsx — General settings with progressive disclosure override (FE-3.4)
// Power user toggle: "Show all features" immediately unlocks all nav items.

import { useOnboardingStore } from "../store/onboarding-store";
import { useUpdateSettings } from "../hooks/useOnboarding";

export function GeneralSettingsForm() {
  const { showAllFeatures, setShowAllFeatures } = useOnboardingStore();
  const updateSettings = useUpdateSettings();

  const handleToggle = () => {
    const nextValue = !showAllFeatures;
    // Optimistic update — apply immediately before API call
    setShowAllFeatures(nextValue);
    updateSettings.mutate({ show_all_features: nextValue });
  };

  return (
    <section aria-label="Progressive disclosure settings">
      <h3 className="text-sm font-semibold text-foreground mb-2">Show all features</h3>
      <div className="flex items-center justify-between gap-4 py-4">
        <div>
          <span
            id="show-all-features-label"
            className="text-sm font-medium text-foreground"
          >
            Unlock all features regardless of progress
          </span>
          <p id="show-all-features-desc" className="text-xs text-muted-foreground mt-0.5">
            Show all navigation items immediately without waiting for milestones.
          </p>
        </div>

        {/* Switch — accessible toggle */}
        <button
          id="show-all-features"
          type="button"
          role="switch"
          aria-checked={showAllFeatures}
          aria-labelledby="show-all-features-label"
          aria-describedby="show-all-features-desc"
          onClick={handleToggle}
          disabled={updateSettings.isPending}
          data-testid="show-all-features-toggle"
          className={[
            "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
            "disabled:cursor-not-allowed disabled:opacity-50",
            showAllFeatures ? "bg-primary" : "bg-muted",
          ].join(" ")}
        >
          <span
            aria-hidden="true"
            className={[
              "inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform",
              showAllFeatures ? "translate-x-6" : "translate-x-1",
            ].join(" ")}
          />
        </button>
      </div>
    </section>
  );
}
