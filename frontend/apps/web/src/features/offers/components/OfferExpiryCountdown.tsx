"use client";

// OfferExpiryCountdown.tsx — FE-12.5: Countdown to offer expiry
// Shows "X days Y hours remaining", red styling when <24h.

import * as React from "react";

interface OfferExpiryCountdownProps {
  expiryDate: string;
}

interface TimeRemaining {
  days: number;
  hours: number;
  minutes: number;
  totalMs: number;
}

function computeRemaining(expiryDate: string): TimeRemaining {
  const now = Date.now();
  const expiry = new Date(expiryDate).getTime();
  const totalMs = Math.max(0, expiry - now);

  const totalMinutes = Math.floor(totalMs / 60_000);
  const totalHours = Math.floor(totalMinutes / 60);
  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;
  const minutes = totalMinutes % 60;

  return { days, hours, minutes, totalMs };
}

export function OfferExpiryCountdown({ expiryDate }: OfferExpiryCountdownProps) {
  const [remaining, setRemaining] = React.useState<TimeRemaining>(() =>
    computeRemaining(expiryDate),
  );

  React.useEffect(() => {
    // Update every minute
    const interval = setInterval(() => {
      setRemaining(computeRemaining(expiryDate));
    }, 60_000);

    // Also re-compute immediately when expiryDate changes
    setRemaining(computeRemaining(expiryDate));

    return () => clearInterval(interval);
  }, [expiryDate]);

  const isExpired = remaining.totalMs <= 0;
  const isUrgent = remaining.totalMs > 0 && remaining.totalMs < 24 * 60 * 60 * 1000;

  if (isExpired) {
    return (
      <div
        data-testid="offer-expiry-countdown"
        className="inline-flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400"
      >
        <span data-testid="expiry-icon" aria-hidden="true">
          &#x23F0;
        </span>
        <span data-testid="expiry-text">Offer expired</span>
      </div>
    );
  }

  // Build readable text
  const parts: string[] = [];
  if (remaining.days > 0) {
    parts.push(`${remaining.days} day${remaining.days !== 1 ? "s" : ""}`);
  }
  if (remaining.hours > 0 || remaining.days > 0) {
    parts.push(`${remaining.hours} hour${remaining.hours !== 1 ? "s" : ""}`);
  }
  if (remaining.days === 0) {
    parts.push(`${remaining.minutes} minute${remaining.minutes !== 1 ? "s" : ""}`);
  }
  const timeText = `${parts.join(" ")} remaining`;

  return (
    <div
      data-testid="offer-expiry-countdown"
      className={`inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium ${
        isUrgent
          ? "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400"
          : "border-border bg-muted/50 text-foreground"
      }`}
    >
      <span data-testid="expiry-icon" aria-hidden="true">
        {isUrgent ? "\u23F0" : "\u231B"}
      </span>
      <span data-testid="expiry-text">{timeText}</span>
    </div>
  );
}
