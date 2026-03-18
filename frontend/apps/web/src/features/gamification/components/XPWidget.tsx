"use client";

// XPWidget — FE-8.2
// Persistent widget showing XP, streak, and league tier.
// Mounts in Sidebar footer (desktop) and Dashboard header (mobile).

import { useRef, useEffect, useState } from "react";
import { Flame, Trophy } from "lucide-react";
import { useGamificationStatus } from "../hooks/useGamification";
import type { LeagueTier } from "../hooks/useGamification";

const LEAGUE_COLORS: Record<LeagueTier, string> = {
  Bronze: "text-amber-700",
  Silver: "text-slate-400",
  Gold: "text-yellow-500",
  Diamond: "text-cyan-400",
};

interface XPWidgetProps {
  /** Compact: shows only icons (for collapsed sidebar) */
  compact?: boolean;
}

export function XPWidget({ compact = false }: XPWidgetProps) {
  const { data } = useGamificationStatus();
  const [displayXp, setDisplayXp] = useState(data?.xp ?? 0);
  const prevXpRef = useRef<number | undefined>(undefined);

  // Cache the prefers-reduced-motion query result in a ref — avoids querying on every XP change
  const prefersReducedMotionRef = useRef(false);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    prefersReducedMotionRef.current = mql.matches;
    const handler = (e: MediaQueryListEvent) => {
      prefersReducedMotionRef.current = e.matches;
    };
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  // Count-up animation when XP changes
  useEffect(() => {
    if (data?.xp === undefined) return;

    if (prevXpRef.current === undefined) {
      // First render — set without animation
      setDisplayXp(data.xp);
      prevXpRef.current = data.xp;
      return;
    }

    if (prevXpRef.current === data.xp) return;

    const start = prevXpRef.current;
    const end = data.xp;
    const duration = 400;
    const startTime = Date.now();

    // Respect prefers-reduced-motion (cached)
    if (prefersReducedMotionRef.current) {
      setDisplayXp(end);
      prevXpRef.current = data.xp;
      return;
    }

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      setDisplayXp(Math.round(start + (end - start) * progress));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
    prevXpRef.current = data.xp;
  }, [data?.xp]);

  if (!data) return null;

  const leagueColorClass = LEAGUE_COLORS[data.leagueTier] ?? "text-foreground";

  if (compact) {
    return (
      <div
        className="flex flex-col items-center gap-1 py-2"
        data-testid="xp-widget-compact"
      >
        <span
          aria-live="polite"
          aria-label={`XP: ${data.xp} points`}
          className="font-mono text-xs tabular-nums"
        >
          {displayXp}
        </span>
        <Flame className="h-4 w-4 text-orange-500" aria-hidden="true" />
        <span className="text-xs text-muted-foreground">{data.streakDays}</span>
      </div>
    );
  }

  return (
    <div
      className="px-3 py-2 space-y-1.5"
      data-testid="xp-widget"
    >
      {/* XP counter */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">XP</span>
        <span
          aria-live="polite"
          aria-label={`XP: ${data.xp} points`}
          className="font-mono text-sm font-semibold tabular-nums"
        >
          {displayXp.toLocaleString()}
        </span>
      </div>

      {/* Streak */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">Streak</span>
        <span
          aria-label={`Streak: ${data.streakDays} days`}
          className="flex items-center gap-1 text-sm"
        >
          <Flame className="h-3.5 w-3.5 text-orange-500" aria-hidden="true" />
          <span className="font-semibold">{data.streakDays}d</span>
        </span>
      </div>

      {/* League */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">League</span>
        <span
          aria-label={`League: ${data.leagueTier}`}
          className={`flex items-center gap-1 text-sm font-medium ${leagueColorClass}`}
        >
          <Trophy className="h-3.5 w-3.5" aria-hidden="true" />
          {data.leagueTier}
        </span>
      </div>
    </div>
  );
}
