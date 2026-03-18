"use client";

// ActivityHeatmap — FE-8.3
// GitHub-style 52-week activity heatmap using custom SVG grid.

import { useState } from "react";
import type { ActivityDay } from "../hooks/useGamification";

const CELL_SIZE = 12;
const CELL_GAP = 2;
const WEEKS = 52;
const DAYS = 7;

// Intensity thresholds for colour levels
function getIntensity(count: number): 0 | 1 | 2 | 3 | 4 {
  if (count === 0) return 0;
  if (count <= 2) return 1;
  if (count <= 5) return 2;
  if (count <= 10) return 3;
  return 4;
}

const INTENSITY_CLASSES: Record<0 | 1 | 2 | 3 | 4, string> = {
  0: "fill-muted",
  1: "fill-emerald-200 dark:fill-emerald-900",
  2: "fill-emerald-400 dark:fill-emerald-700",
  3: "fill-emerald-600 dark:fill-emerald-500",
  4: "fill-emerald-800 dark:fill-emerald-300",
};

function formatDateForLocale(date: string, locale: string): string {
  try {
    return new Intl.DateTimeFormat(locale, {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(new Date(date));
  } catch {
    return date;
  }
}

interface HeatmapCellProps {
  date: string;
  count: number;
  xpEarned: number;
  x: number;
  y: number;
  locale: string;
}

function HeatmapCell({ date, count, xpEarned, x, y, locale }: HeatmapCellProps) {
  const [isHovered, setIsHovered] = useState(false);
  const intensity = getIntensity(count);
  const formattedDate = formatDateForLocale(date, locale);
  const tooltipText = `${formattedDate}: ${count} activities, ${xpEarned} XP`;

  // Bounds-check tooltip position to prevent overflow on narrow viewports
  const tooltipWidth = 150;
  const tooltipHeight = 28;
  const svgWidth = WEEKS * (CELL_SIZE + CELL_GAP);
  // Clamp X so tooltip doesn't overflow left or right edge
  const rawTooltipX = x - (tooltipWidth / 2) + (CELL_SIZE / 2);
  const clampedX = Math.max(0, Math.min(rawTooltipX, svgWidth - tooltipWidth));
  // If cell is near the top, show tooltip below instead of above
  const showBelow = y < tooltipHeight + 4;
  const tooltipY = showBelow ? y + CELL_SIZE + 4 : y - tooltipHeight - 4;

  return (
    <g className="relative">
      <rect
        x={x}
        y={y}
        width={CELL_SIZE}
        height={CELL_SIZE}
        rx={2}
        className={INTENSITY_CLASSES[intensity]}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onFocus={() => setIsHovered(true)}
        onBlur={() => setIsHovered(false)}
        onTouchStart={() => setIsHovered(true)}
        tabIndex={0}
        aria-label={tooltipText}
        role="img"
      />
      {isHovered && (
        <foreignObject
          x={clampedX}
          y={tooltipY}
          width={tooltipWidth}
          height={tooltipHeight}
          className="pointer-events-none overflow-visible"
        >
          <div
            role="tooltip"
            className="whitespace-nowrap bg-popover text-popover-foreground text-xs px-2 py-1 rounded shadow pointer-events-none"
          >
            {tooltipText}
          </div>
        </foreignObject>
      )}
    </g>
  );
}

interface ActivityHeatmapProps {
  days: ActivityDay[];
  locale?: string;
}

export function ActivityHeatmap({ days, locale = "en-IN" }: ActivityHeatmapProps) {
  // Build a 52x7 grid from the data
  const dayCountMap = new Map<string, number>(
    days.map((d) => [d.date.substring(0, 10), d.count])
  );
  const dayXpMap = new Map<string, number>(
    days.map((d) => [d.date.substring(0, 10), d.xpEarned])
  );

  // Find most active day for accessibility summary
  const mostActive = days.reduce<ActivityDay | null>((best, day) => {
    if (!best || day.count > best.count) return day;
    return best;
  }, null);

  // Generate grid cells: 52 weeks × 7 days
  const today = new Date();
  const cells: Array<{ date: string; count: number; xpEarned: number; week: number; day: number }> = [];

  for (let week = 0; week < WEEKS; week++) {
    for (let day = 0; day < DAYS; day++) {
      const daysAgo = (WEEKS - 1 - week) * 7 + (DAYS - 1 - day);
      const cellDate = new Date(today);
      cellDate.setDate(today.getDate() - daysAgo);
      const dateStr = cellDate.toISOString().substring(0, 10);
      cells.push({
        date: dateStr,
        count: dayCountMap.get(dateStr) ?? 0,
        xpEarned: dayXpMap.get(dateStr) ?? 0,
        week,
        day,
      });
    }
  }

  const svgWidth = WEEKS * (CELL_SIZE + CELL_GAP);
  const svgHeight = DAYS * (CELL_SIZE + CELL_GAP);

  return (
    <div
      aria-label="Activity heatmap for the past 52 weeks"
      role="img"
      className="overflow-x-auto"
    >
      {mostActive && (
        <p className="sr-only">
          {`Most active: ${formatDateForLocale(mostActive.date, locale)} with ${mostActive.count} activities`}
        </p>
      )}
      <svg
        width={svgWidth}
        height={svgHeight}
        aria-hidden="true"
        className="block"
      >
        {cells.map((cell) => (
          <HeatmapCell
            key={`${cell.week}-${cell.day}`}
            date={cell.date}
            count={cell.count}
            xpEarned={cell.xpEarned}
            x={cell.week * (CELL_SIZE + CELL_GAP)}
            y={cell.day * (CELL_SIZE + CELL_GAP)}
            locale={locale}
          />
        ))}
      </svg>
    </div>
  );
}
