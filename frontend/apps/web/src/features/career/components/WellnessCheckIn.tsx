"use client";

// WellnessCheckIn — FE-13.2
// Mood and energy check-in form with emoji radio buttons and range slider.

import { useState, useMemo } from "react";
import { useWellnessCheckIn, useWellnessTrend } from "../hooks/useWellness";
import type { MoodLevel } from "../types";

const MOOD_OPTIONS: { value: MoodLevel; emoji: string; label: string }[] = [
  { value: 1, emoji: "\uD83D\uDE1E", label: "Very unhappy" },
  { value: 2, emoji: "\uD83D\uDE41", label: "Unhappy" },
  { value: 3, emoji: "\uD83D\uDE10", label: "Neutral" },
  { value: 4, emoji: "\uD83D\uDE42", label: "Happy" },
  { value: 5, emoji: "\uD83D\uDE04", label: "Very happy" },
];

const ENERGY_LABELS: Record<number, string> = {
  1: "Very low",
  2: "Low",
  3: "Moderate",
  4: "High",
  5: "Very high",
};

export function WellnessCheckIn() {
  const [mood, setMood] = useState<MoodLevel | null>(null);
  const [energy, setEnergy] = useState<MoodLevel>(3);
  const [checkedIn, setCheckedIn] = useState(false);

  const mutation = useWellnessCheckIn();
  const { data: trend } = useWellnessTrend();

  // Check if there's already a check-in for today
  const todayStr = new Date().toISOString().split("T")[0];
  const hasCheckedInToday = useMemo(() => {
    if (!trend?.data) return false;
    return trend.data.some((entry) => entry.date.startsWith(todayStr));
  }, [trend?.data, todayStr]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (mood === null) return;
    mutation.mutate(
      { mood, energy },
      {
        onSuccess: () => setCheckedIn(true),
      },
    );
  }

  if (checkedIn || hasCheckedInToday) {
    return (
      <div data-testid="wellness-checkin">
        <div data-testid="checked-in-state" className="rounded-md bg-green-50 p-4 text-center">
          <p className="text-sm font-medium text-green-800">Checked in today</p>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="wellness-checkin">
      <form onSubmit={handleSubmit} className="space-y-4">
        <fieldset>
          <legend className="text-sm font-medium mb-2">How are you feeling?</legend>
          <div className="flex gap-2">
            {MOOD_OPTIONS.map((option) => (
              <label
                key={option.value}
                className={`flex flex-col items-center gap-1 cursor-pointer rounded-md p-2 transition-colors ${
                  mood === option.value
                    ? "bg-primary/10 ring-2 ring-primary"
                    : "hover:bg-muted"
                }`}
              >
                <input
                  type="radio"
                  name="mood"
                  data-testid={`mood-${option.value}`}
                  value={option.value}
                  checked={mood === option.value}
                  onChange={() => setMood(option.value)}
                  aria-label={option.label}
                  className="sr-only"
                />
                <span className="text-2xl" aria-hidden="true">
                  {option.emoji}
                </span>
                <span className="text-xs text-muted-foreground">{option.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <div>
          <label htmlFor="energy-slider" className="block text-sm font-medium mb-2">
            Energy level: <span className="font-semibold">{energy}</span>{" "}
            <span className="text-muted-foreground font-normal">({ENERGY_LABELS[energy]})</span>
          </label>
          <div className="relative pt-1">
            <input
              id="energy-slider"
              data-testid="energy-slider"
              type="range"
              min={1}
              max={5}
              step={1}
              value={energy}
              onChange={(e) => setEnergy(Number(e.target.value) as MoodLevel)}
              aria-label={`Energy level: ${energy}`}
              aria-valuetext={ENERGY_LABELS[energy]}
              className="w-full h-2 appearance-none rounded-full bg-muted cursor-pointer accent-primary [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary [&::-webkit-slider-thumb]:shadow-md [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-background"
            />
            {/* Track fill indicator */}
            <div
              className="absolute top-1 left-0 h-2 rounded-full bg-primary/30 pointer-events-none"
              style={{ width: `${((energy - 1) / 4) * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>Low</span>
            <span>High</span>
          </div>
        </div>

        <button
          type="submit"
          data-testid="checkin-submit"
          disabled={mood === null || mutation.isPending}
          aria-disabled={mood === null || mutation.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {mutation.isPending ? "Submitting\u2026" : "Submit check-in"}
        </button>
      </form>
    </div>
  );
}
