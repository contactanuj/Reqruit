"use client";

// Sidebar.tsx — Desktop sidebar navigation (FE-2.1, FE-3.3, FE-3.4)
// Updated to support progressive disclosure: locked items greyed out, newly unlocked items highlighted.
// Settings section with sub-items. Uses barrel imports only (Rule 8).

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Briefcase,
  ClipboardList,
  CalendarCheck,
  HandCoins,
  TrendingUp,
  User,
  Settings,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Sun,
  Moon,
  Monitor,
  LogOut,
} from "lucide-react";
import { useLayoutStore } from "@/features/shell/store/layout-store";
import { useThemeStore } from "@/features/shell/store/theme-store";
import { useLogout } from "@/features/auth";
import {
  useProgressiveDisclosure,
  useOnboardingStore,
} from "@/features/onboarding";
import type { FeatureKey } from "@/features/onboarding";
import { XPWidget } from "@/features/gamification/components/XPWidget";
import { CreditCounter } from "@/features/credits/components/CreditCounter";

const navItems: Array<{
  href: string;
  label: string;
  icon: React.ElementType;
  featureKey: FeatureKey;
}> = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, featureKey: "dashboard" },
  { href: "/jobs", label: "Jobs", icon: Briefcase, featureKey: "jobs" },
  { href: "/applications", label: "Applications", icon: ClipboardList, featureKey: "applications" },
  { href: "/interviews", label: "Interviews", icon: CalendarCheck, featureKey: "interviews" },
  { href: "/offers", label: "Offers", icon: HandCoins, featureKey: "offers" },
  { href: "/career", label: "Career", icon: TrendingUp, featureKey: "career" },
  { href: "/profile", label: "Profile", icon: User, featureKey: "profile" },
];

const settingsSubItems = [
  { href: "/settings/general", label: "General" },
  { href: "/settings/account", label: "Account" },
  { href: "/settings/notifications", label: "Notifications" },
  { href: "/settings/usage", label: "Usage" },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar } = useLayoutStore();
  const { theme, setTheme } = useThemeStore();
  const logout = useLogout();
  const featureVisibility = useProgressiveDisclosure();
  const markFeatureSeen = useOnboardingStore((s) => s.markFeatureSeen);
  const [settingsOpen, setSettingsOpen] = useState(
    () => pathname.startsWith("/settings"),
  );

  // Collect newly unlocked features that the user is currently viewing
  // so we can mark them as seen in a useEffect (never during render).
  const activeNewlyUnlocked = useMemo(() => {
    const keys: FeatureKey[] = [];
    for (const { href, featureKey } of navItems) {
      const isActive =
        href === "/dashboard"
          ? pathname === "/dashboard"
          : pathname.startsWith(href);
      if (isActive && featureVisibility[featureKey]?.newlyUnlocked) {
        keys.push(featureKey);
      }
    }
    return keys;
  }, [pathname, featureVisibility]);

  useEffect(() => {
    for (const key of activeNewlyUnlocked) {
      markFeatureSeen(key);
    }
  }, [activeNewlyUnlocked, markFeatureSeen]);

  const isSettingsActive = pathname.startsWith("/settings");

  return (
    <aside
      aria-label="Application sidebar"
      data-testid="sidebar"
      className={[
        "hidden md:flex flex-col h-full bg-card border-e border-border",
        "transition-[width] duration-200 ease-in-out motion-reduce:transition-none",
        sidebarCollapsed ? "w-14" : "w-[220px]",
      ].join(" ")}
    >
      {/* Collapse toggle */}
      <div className="flex justify-end p-2">
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="p-1.5 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          ) : (
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          )}
        </button>
      </div>

      {/* Navigation links */}
      <nav aria-label="Primary navigation" className="flex-1 px-2 space-y-1 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon, featureKey }) => {
          const isActive =
            href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(href);
          const visibility = featureVisibility[featureKey];
          const isEnabled = visibility.enabled;
          const isNewlyUnlocked = visibility.newlyUnlocked;
          const lockedHint = visibility.lockedHint;

          if (!isEnabled) {
            return (
              <div
                key={href}
                title={lockedHint}
                aria-disabled="true"
                data-testid={`nav-locked-${featureKey}`}
                className={[
                  "flex items-center gap-3 rounded-md ps-2 pe-2 py-2 text-sm font-medium",
                  "opacity-50 cursor-not-allowed text-muted-foreground",
                  sidebarCollapsed ? "justify-center" : "",
                ].join(" ")}
              >
                <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                {!sidebarCollapsed && <span>{label}</span>}
              </div>
            );
          }

          return (
            <Link
              key={href}
              href={href}
              aria-current={isActive ? "page" : undefined}
              className={[
                "flex items-center gap-3 rounded-md ps-2 pe-2 py-2 text-sm font-medium transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground",
                sidebarCollapsed ? "justify-center" : "",
                // Newly unlocked highlight (respects prefers-reduced-motion via CSS)
                isNewlyUnlocked
                  ? "ring-2 ring-primary animate-pulse motion-reduce:animate-none motion-reduce:ring-2"
                  : "",
              ].join(" ")}
            >
              <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
              {!sidebarCollapsed && <span>{label}</span>}
            </Link>
          );
        })}

        {/* Settings section with sub-items */}
        {!sidebarCollapsed ? (
          <div>
            <button
              type="button"
              onClick={() => setSettingsOpen((prev) => !prev)}
              aria-expanded={settingsOpen}
              aria-controls="settings-sub-nav"
              className={[
                "w-full flex items-center gap-3 rounded-md ps-2 pe-2 py-2 text-sm font-medium transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                isSettingsActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground",
              ].join(" ")}
            >
              <Settings className="h-5 w-5 shrink-0" aria-hidden="true" />
              <span className="flex-1 text-start">Settings</span>
              <ChevronDown
                className={[
                  "h-4 w-4 shrink-0 transition-transform",
                  settingsOpen ? "rotate-180" : "",
                ].join(" ")}
                aria-hidden="true"
              />
            </button>
            {settingsOpen && (
              <ul id="settings-sub-nav" role="list" className="ms-7 space-y-0.5 mt-0.5">
                {settingsSubItems.map(({ href, label }) => {
                  const isSubActive = pathname === href;
                  return (
                    <li key={href}>
                      <Link
                        href={href}
                        aria-current={isSubActive ? "page" : undefined}
                        className={[
                          "block rounded-md ps-2 pe-2 py-1.5 text-sm transition-colors",
                          "hover:bg-accent hover:text-accent-foreground",
                          isSubActive
                            ? "bg-accent text-accent-foreground font-medium"
                            : "text-muted-foreground",
                        ].join(" ")}
                      >
                        {label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        ) : (
          <Link
            href="/settings/general"
            aria-label="Settings"
            aria-current={isSettingsActive ? "page" : undefined}
            className={[
              "flex items-center justify-center rounded-md ps-2 pe-2 py-2 text-sm font-medium transition-colors",
              "hover:bg-accent hover:text-accent-foreground",
              isSettingsActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground",
            ].join(" ")}
          >
            <Settings className="h-5 w-5 shrink-0" aria-hidden="true" />
          </Link>
        )}
      </nav>

      {/* XP / Credits footer widgets (FE-8.2, FE-8.6) */}
      <div className="border-t border-border">
        <XPWidget compact={sidebarCollapsed} />
        {!sidebarCollapsed && <CreditCounter />}
      </div>

      {/* Bottom section: theme toggle + logout */}
      <div className="p-2 space-y-1 border-t border-border">
        {/* Theme toggle */}
        <div
          className={[
            "flex rounded-md overflow-hidden",
            sidebarCollapsed ? "flex-col" : "flex-row",
          ].join(" ")}
          role="group"
          aria-label="Theme"
        >
          {(
            [
              { value: "light", icon: Sun, label: "Light mode" },
              { value: "system", icon: Monitor, label: "System theme" },
              { value: "dark", icon: Moon, label: "Dark mode" },
            ] as const
          ).map(({ value, icon: Icon, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => setTheme(value)}
              aria-label={label}
              aria-pressed={theme === value}
              className={[
                "flex-1 flex items-center justify-center p-1.5 text-xs transition-colors",
                theme === value
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-accent text-muted-foreground",
              ].join(" ")}
            >
              <Icon className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          ))}
        </div>

        {/* Logout */}
        <button
          type="button"
          onClick={() => logout.mutate()}
          disabled={logout.isPending}
          aria-label="Log out"
          className={[
            "w-full flex items-center gap-3 rounded-md ps-2 pe-2 py-2 text-sm font-medium",
            "text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors",
            sidebarCollapsed ? "justify-center" : "",
          ].join(" ")}
        >
          <LogOut className="h-5 w-5 shrink-0" aria-hidden="true" />
          {!sidebarCollapsed && (
            <span>{logout.isPending ? "Logging out..." : "Log out"}</span>
          )}
        </button>
      </div>
    </aside>
  );
}
