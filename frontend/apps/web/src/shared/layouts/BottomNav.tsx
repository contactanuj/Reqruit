"use client";

// BottomNav.tsx — Mobile bottom tab bar (FE-2.2, FE-3.3, FE-3.4)
// Visible only on ≤767px (md:hidden). Tap targets ≥44×44px.
// Updated to support progressive disclosure: locked items greyed out with tooltips.

import { useEffect, useMemo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Briefcase,
  ClipboardList,
  Bot,
  User,
  Search,
} from "lucide-react";
import { useLayoutStore } from "@/features/shell/store/layout-store";
import {
  useProgressiveDisclosure,
  useOnboardingStore,
} from "@/features/onboarding";
import type { FeatureKey } from "@/features/onboarding";

const tabs: Array<{ href: string; label: string; icon: React.ElementType; featureKey: FeatureKey | "copilot" }> = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, featureKey: "dashboard" },
  { href: "/jobs", label: "Jobs", icon: Briefcase, featureKey: "jobs" },
  { href: "/applications", label: "Applications", icon: ClipboardList, featureKey: "applications" },
  { href: "/copilot", label: "Copilot", icon: Bot, featureKey: "copilot" },
  { href: "/profile", label: "Profile", icon: User, featureKey: "profile" },
] as const;

export function BottomNav() {
  const pathname = usePathname();
  const { toggleCopilot, setCommandPaletteOpen } = useLayoutStore();
  const featureVisibility = useProgressiveDisclosure();
  const markFeatureSeen = useOnboardingStore((s) => s.markFeatureSeen);

  // Mark newly unlocked features as seen when the user is on that tab
  const activeNewlyUnlocked = useMemo(() => {
    const keys: FeatureKey[] = [];
    for (const { href, featureKey } of tabs) {
      if (featureKey === "copilot") continue;
      const isActive =
        href === "/dashboard"
          ? pathname === "/dashboard"
          : pathname.startsWith(href);
      if (isActive && featureVisibility[featureKey as FeatureKey]?.newlyUnlocked) {
        keys.push(featureKey as FeatureKey);
      }
    }
    return keys;
  }, [pathname, featureVisibility]);

  useEffect(() => {
    for (const key of activeNewlyUnlocked) {
      markFeatureSeen(key);
    }
  }, [activeNewlyUnlocked, markFeatureSeen]);

  return (
    <div className="md:hidden" aria-hidden="false">
      {/* Search FAB — bottom right, above tab bar */}
      <button
        type="button"
        onClick={() => setCommandPaletteOpen(true)}
        className="fixed bottom-20 end-4 z-40 flex items-center justify-center w-12 h-12 rounded-full bg-primary text-primary-foreground shadow-lg"
        aria-label="Search"
        data-testid="search-fab"
      >
        <Search className="h-5 w-5" />
      </button>

      <nav
        aria-label="Mobile bottom navigation"
        data-testid="bottom-nav"
        className="fixed bottom-0 start-0 end-0 z-50 bg-card border-t border-border"
      >
      <ul className="flex" role="list">
        {tabs.map(({ href, label, icon: Icon, featureKey }) => {
          const isActive =
            href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(href);

          // Copilot tab always visible/enabled — not governed by progressive disclosure
          if (href === "/copilot") {
            return (
              <li key={href} className="flex-1">
                <button
                  type="button"
                  onClick={toggleCopilot}
                  aria-label={label}
                  aria-current={isActive ? "page" : undefined}
                  className={[
                    "flex flex-col items-center justify-center w-full min-h-[44px] min-w-[44px] py-2 gap-1",
                    "text-xs transition-colors",
                    isActive
                      ? "text-primary"
                      : "text-muted-foreground hover:text-foreground",
                  ].join(" ")}
                >
                  <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                  <span>{label}</span>
                </button>
              </li>
            );
          }

          const visibility = featureVisibility[featureKey as FeatureKey];
          const isEnabled = visibility?.enabled ?? true;
          const isNewlyUnlocked = visibility?.newlyUnlocked ?? false;
          const lockedHint = visibility?.lockedHint;

          if (!isEnabled) {
            return (
              <li key={href} className="flex-1">
                <div
                  aria-label={label}
                  aria-disabled="true"
                  title={lockedHint}
                  data-testid={`bottom-nav-locked-${featureKey}`}
                  className={[
                    "flex flex-col items-center justify-center min-h-[44px] min-w-[44px] py-2 gap-1",
                    "text-xs opacity-50 cursor-not-allowed text-muted-foreground",
                  ].join(" ")}
                >
                  <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                  <span>{label}</span>
                </div>
              </li>
            );
          }

          return (
            <li key={href} className="flex-1">
              <Link
                href={href}
                aria-label={label}
                aria-current={isActive ? "page" : undefined}
                className={[
                  "flex flex-col items-center justify-center min-h-[44px] min-w-[44px] py-2 gap-1",
                  "text-xs transition-colors",
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground hover:text-foreground",
                  isNewlyUnlocked
                    ? "ring-2 ring-primary animate-pulse motion-reduce:animate-none"
                    : "",
                ].join(" ")}
              >
                <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                <span>{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
    </div>
  );
}
