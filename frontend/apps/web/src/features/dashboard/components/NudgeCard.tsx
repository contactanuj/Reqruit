"use client";

// NudgeCard — FE-8.5
// Actionable nudge card with dismiss functionality.

import Link from "next/link";
import { Bell, Calendar, Eye, MessageCircle, X } from "lucide-react";
import type { Nudge, NudgeType } from "../hooks/useDashboard";

const NUDGE_ICON: Record<NudgeType, React.ElementType> = {
  follow_up: MessageCircle,
  interview_prep: Calendar,
  ghost_job: Eye,
  deadline: Bell,
};

interface NudgeCardProps {
  nudge: Nudge;
  onDismiss: (id: string) => void;
  isDismissing?: boolean;
}

export function NudgeCard({ nudge, onDismiss, isDismissing }: NudgeCardProps) {
  const Icon = NUDGE_ICON[nudge.type] ?? Bell;

  return (
    <div
      role="article"
      aria-label={`Nudge: ${nudge.message}`}
      className="flex items-start gap-3 rounded-lg border border-border bg-card p-4"
      data-testid={`nudge-card-${nudge.id}`}
    >
      <Icon className="h-5 w-5 shrink-0 text-primary mt-0.5" aria-hidden="true" />

      <div className="flex-1 min-w-0">
        <p className="text-sm">{nudge.message}</p>
        <Link
          href={nudge.ctaHref}
          className="mt-2 inline-block rounded-md bg-primary px-3 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          {nudge.ctaLabel}
        </Link>
      </div>

      <button
        type="button"
        onClick={() => onDismiss(nudge.id)}
        disabled={isDismissing}
        aria-label="Dismiss nudge"
        className="shrink-0 rounded-md p-1 text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-50"
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
}
