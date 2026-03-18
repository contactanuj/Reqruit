// FeatureUnlockToast.tsx — Feature unlock notification (FE-3.3)
// Uses sonner toast with 5000ms duration. aria-live="assertive" for immediate announcement.

import { toast } from "sonner";
import { Unlock } from "lucide-react";

export interface FeatureUnlockToastProps {
  featureName: string;
}

/**
 * Programmatically fire a feature unlock toast via sonner.
 * Call this after a milestone event (e.g. status → Interviewing).
 */
export function showFeatureUnlockToast(featureName: string): void {
  toast.custom(
    () => (
      <div
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
        className="flex items-center gap-3 rounded-lg bg-background border border-border shadow-lg px-4 py-3"
        data-testid="feature-unlock-toast"
      >
        <Unlock
          className="h-5 w-5 text-primary shrink-0"
          aria-hidden="true"
        />
        <div>
          <p className="text-sm font-semibold text-foreground">Feature unlocked!</p>
          <p className="text-xs text-muted-foreground">{featureName} is now available</p>
        </div>
      </div>
    ),
    {
      duration: 5000,
    },
  );
}

/**
 * Declarative component variant — renders a static unlock notification.
 * Useful for testing and Storybook.
 */
export function FeatureUnlockToast({ featureName }: FeatureUnlockToastProps) {
  return (
    <div
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
      className="flex items-center gap-3 rounded-lg bg-background border border-border shadow-lg px-4 py-3"
      data-testid="feature-unlock-toast"
    >
      <Unlock className="h-5 w-5 text-primary shrink-0" aria-hidden="true" />
      <div>
        <p className="text-sm font-semibold text-foreground">Feature unlocked!</p>
        <p className="text-xs text-muted-foreground">{featureName} is now available</p>
      </div>
    </div>
  );
}
