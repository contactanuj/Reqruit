"use client";

// Settings -> Notifications page (FE-8.4)
// Per-type toggles, quiet hours, and push subscribe/unsubscribe.

import { useState, useEffect, useRef, useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, queryKeys } from "@reqruit/api-client";
import { useWebPush } from "@/shared/notifications/useWebPush";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface NotificationPreferences {
  interviewReminders: boolean;
  newJobMatches: boolean;
  applicationFollowUp: boolean;
  offerDeadlines: boolean;
  quietHoursStart: string; // HH:mm
  quietHoursEnd: string;   // HH:mm
}

const DEFAULT_PREFS: NotificationPreferences = {
  interviewReminders: true,
  newJobMatches: true,
  applicationFollowUp: true,
  offerDeadlines: true,
  quietHoursStart: "22:00",
  quietHoursEnd: "08:00",
};

const TOGGLE_OPTIONS: Array<{
  key: keyof Pick<
    NotificationPreferences,
    "interviewReminders" | "newJobMatches" | "applicationFollowUp" | "offerDeadlines"
  >;
  label: string;
  description: string;
}> = [
  {
    key: "interviewReminders",
    label: "Interview reminders",
    description: "Get notified before upcoming interviews",
  },
  {
    key: "newJobMatches",
    label: "New job matches",
    description: "Alerts when new jobs match your profile",
  },
  {
    key: "applicationFollowUp",
    label: "Application follow-up nudges",
    description: "Reminders to follow up on pending applications",
  },
  {
    key: "offerDeadlines",
    label: "Offer deadlines",
    description: "Alerts when offer deadlines are approaching",
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function NotificationsSettingsPage() {
  const queryClient = useQueryClient();
  const { isSupported, isSubscribed, permission, subscribe, unsubscribe, isLoading, error } =
    useWebPush();

  // Fetch existing preferences
  const { data: savedPrefs, isPending: isLoadingPrefs } = useQuery<NotificationPreferences>({
    queryKey: queryKeys.notifications.preferences(),
    queryFn: () =>
      apiClient.get<NotificationPreferences>("/notifications/preferences"),
  });

  const [prefs, setPrefs] = useState<NotificationPreferences>(DEFAULT_PREFS);

  // Sync fetched prefs into local state
  useEffect(() => {
    if (savedPrefs) {
      setPrefs(savedPrefs);
    }
  }, [savedPrefs]);

  // Debounced auto-save mutation
  const saveMutation = useMutation({
    mutationFn: (newPrefs: NotificationPreferences) =>
      apiClient.put("/notifications/preferences", newPrefs),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.preferences(),
      });
    },
    onError: () => {
      toast.error("Failed to save notification preferences");
    },
  });

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const saveWithDebounce = useCallback(
    (newPrefs: NotificationPreferences) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = setTimeout(() => {
        saveMutation.mutate(newPrefs);
      }, 300);
    },
    [saveMutation],
  );

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  const handleToggle = (key: keyof NotificationPreferences) => {
    const updated = { ...prefs, [key]: !prefs[key] };
    setPrefs(updated);
    saveWithDebounce(updated);
  };

  const handleTimeChange = (
    key: "quietHoursStart" | "quietHoursEnd",
    value: string,
  ) => {
    const updated = { ...prefs, [key]: value };
    setPrefs(updated);
    saveWithDebounce(updated);
  };

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">Notification Settings</h1>

      {/* Push notification toggle */}
      <section className="rounded-xl border border-border bg-card p-6 space-y-4">
        <h2 className="text-lg font-semibold">Push Notifications</h2>

        {!isSupported ? (
          <p className="text-sm text-muted-foreground">
            Push notifications are not supported in this browser.
          </p>
        ) : permission === "denied" ? (
          <div className="space-y-2">
            <p className="text-sm text-destructive">
              Push notifications blocked — enable in browser settings
            </p>
            <p className="text-xs text-muted-foreground">
              To enable: open your browser settings, find Site Settings, and allow
              notifications for this site.
            </p>
          </div>
        ) : isSubscribed ? (
          <div className="flex items-center justify-between">
            <span className="text-sm text-green-600 font-medium">
              Push notifications enabled
            </span>
            <button
              type="button"
              onClick={() => void unsubscribe()}
              disabled={isLoading}
              className="text-sm text-muted-foreground hover:text-destructive transition-colors"
            >
              {isLoading ? "Disabling..." : "Disable"}
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Get reminders for interviews, new job matches, and deadlines.
            </p>
            <button
              type="button"
              onClick={() => void subscribe()}
              disabled={isLoading}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {isLoading ? "Enabling..." : "Enable push notifications"}
            </button>
          </div>
        )}

        {error && (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
      </section>

      {/* Per-type notification toggles */}
      <section className="rounded-xl border border-border bg-card p-6 space-y-4">
        <h2 className="text-lg font-semibold">Notification Types</h2>
        <p className="text-sm text-muted-foreground">
          Choose which notifications you want to receive.
        </p>

        {isLoadingPrefs ? (
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-10 rounded bg-muted animate-pulse motion-reduce:animate-none"
              />
            ))}
          </div>
        ) : (
          <div className="divide-y divide-border">
            {TOGGLE_OPTIONS.map(({ key, label, description }) => (
              <div
                key={key}
                className="flex items-center justify-between py-3"
              >
                <div className="flex-1 min-w-0 pr-4">
                  <p className="text-sm font-medium">{label}</p>
                  <p className="text-xs text-muted-foreground">
                    {description}
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={prefs[key] as boolean}
                  aria-label={label}
                  onClick={() => handleToggle(key)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 ${
                    prefs[key] ? "bg-primary" : "bg-muted"
                  }`}
                  data-testid={`toggle-${key}`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-background shadow-lg ring-0 transition-transform ${
                      prefs[key] ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Quiet hours */}
      <section className="rounded-xl border border-border bg-card p-6 space-y-4">
        <h2 className="text-lg font-semibold">Quiet Hours</h2>
        <p className="text-sm text-muted-foreground">
          Suppress notifications during these hours.
        </p>

        <div className="flex items-center gap-3">
          <div className="flex flex-col gap-1">
            <label
              htmlFor="quiet-start"
              className="text-xs font-medium text-muted-foreground"
            >
              Start
            </label>
            <input
              id="quiet-start"
              type="time"
              value={prefs.quietHoursStart}
              onChange={(e) =>
                handleTimeChange("quietHoursStart", e.target.value)
              }
              className="rounded-md border border-border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              data-testid="quiet-hours-start"
            />
          </div>
          <span className="mt-5 text-sm text-muted-foreground">to</span>
          <div className="flex flex-col gap-1">
            <label
              htmlFor="quiet-end"
              className="text-xs font-medium text-muted-foreground"
            >
              End
            </label>
            <input
              id="quiet-end"
              type="time"
              value={prefs.quietHoursEnd}
              onChange={(e) =>
                handleTimeChange("quietHoursEnd", e.target.value)
              }
              className="rounded-md border border-border bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              data-testid="quiet-hours-end"
            />
          </div>
        </div>
      </section>
    </div>
  );
}
