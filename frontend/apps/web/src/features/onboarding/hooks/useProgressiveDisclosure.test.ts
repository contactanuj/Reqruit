// useProgressiveDisclosure.test.ts — FE-3.4 (AC: #2, #3) + FE-3.1 (AC: #2)

import { describe, it, expect, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { useProgressiveDisclosure, getUnlockFromStatusTransition } from "./useProgressiveDisclosure";
import { useOnboardingStore } from "../store/onboarding-store";

beforeEach(() => {
  useOnboardingStore.setState({
    onboardingComplete: false,
    goal: null,
    unlockedFeatures: {},
    showAllFeatures: false,
  });
});

describe("useProgressiveDisclosure", () => {
  it("returns dashboard and jobs as enabled for default (no goal)", () => {
    const { result } = renderHook(() => useProgressiveDisclosure());
    expect(result.current.dashboard.enabled).toBe(true);
    expect(result.current.jobs.enabled).toBe(true);
    // No goal means only dashboard+jobs enabled
    expect(result.current.interviews.enabled).toBe(false);
    expect(result.current.offers.enabled).toBe(false);
  });

  it("returns goal-scoped features enabled for find_jobs goal", () => {
    useOnboardingStore.setState({ goal: "find_jobs" });
    const { result } = renderHook(() => useProgressiveDisclosure());
    expect(result.current.dashboard.enabled).toBe(true);
    expect(result.current.jobs.enabled).toBe(true);
    expect(result.current.applications.enabled).toBe(true);
    expect(result.current.profile.enabled).toBe(true);
    expect(result.current.interviews.enabled).toBe(false);
    expect(result.current.offers.enabled).toBe(false);
  });

  it("returns interview prep features for interview_prep goal", () => {
    useOnboardingStore.setState({ goal: "interview_prep" });
    const { result } = renderHook(() => useProgressiveDisclosure());
    expect(result.current.interviews.enabled).toBe(true);
    expect(result.current.dashboard.enabled).toBe(true);
    expect(result.current.offers.enabled).toBe(false);
  });

  it("returns offers as enabled for negotiate_offer goal", () => {
    useOnboardingStore.setState({ goal: "negotiate_offer" });
    const { result } = renderHook(() => useProgressiveDisclosure());
    expect(result.current.offers.enabled).toBe(true);
    expect(result.current.jobs.enabled).toBe(false);
  });

  it("all features enabled when showAllFeatures is true (power user override)", () => {
    useOnboardingStore.setState({ goal: "find_jobs", showAllFeatures: true });
    const { result } = renderHook(() => useProgressiveDisclosure());
    expect(result.current.dashboard.enabled).toBe(true);
    expect(result.current.jobs.enabled).toBe(true);
    expect(result.current.applications.enabled).toBe(true);
    expect(result.current.interviews.enabled).toBe(true);
    expect(result.current.offers.enabled).toBe(true);
    expect(result.current.career.enabled).toBe(true);
    expect(result.current.profile.enabled).toBe(true);
  });

  it("disabling showAllFeatures returns milestone-based state", () => {
    useOnboardingStore.setState({
      goal: "find_jobs",
      showAllFeatures: false,
    });
    const { result } = renderHook(() => useProgressiveDisclosure());
    expect(result.current.interviews.enabled).toBe(false);
    expect(result.current.offers.enabled).toBe(false);
  });

  it("milestone-unlocked feature is enabled regardless of goal", () => {
    useOnboardingStore.setState({
      goal: "find_jobs",
      unlockedFeatures: {
        interviews: { key: "interviews", unlockedAt: Date.now(), seen: false },
      },
    });
    const { result } = renderHook(() => useProgressiveDisclosure());
    expect(result.current.interviews.enabled).toBe(true);
  });

  it("newly unlocked feature has newlyUnlocked=true within 10s window", () => {
    useOnboardingStore.setState({
      goal: "find_jobs",
      unlockedFeatures: {
        interviews: { key: "interviews", unlockedAt: Date.now() - 1000, seen: false },
      },
    });
    const { result } = renderHook(() => useProgressiveDisclosure());
    expect(result.current.interviews.newlyUnlocked).toBe(true);
  });

  it("seen feature has newlyUnlocked=false", () => {
    useOnboardingStore.setState({
      goal: "find_jobs",
      unlockedFeatures: {
        interviews: { key: "interviews", unlockedAt: Date.now() - 1000, seen: true },
      },
    });
    const { result } = renderHook(() => useProgressiveDisclosure());
    expect(result.current.interviews.newlyUnlocked).toBe(false);
  });

  it("locked features provide a tooltip hint", () => {
    useOnboardingStore.setState({ goal: "find_jobs" });
    const { result } = renderHook(() => useProgressiveDisclosure());
    expect(result.current.interviews.lockedHint).toContain("Unlocks when");
    expect(result.current.offers.lockedHint).toContain("Unlocks when");
  });

  it("enabled features have no locked hint", () => {
    useOnboardingStore.setState({ goal: "find_jobs" });
    const { result } = renderHook(() => useProgressiveDisclosure());
    expect(result.current.dashboard.lockedHint).toBeUndefined();
    expect(result.current.jobs.lockedHint).toBeUndefined();
  });
});

describe("getUnlockFromStatusTransition", () => {
  it("returns interviews for Interviewing status", () => {
    expect(getUnlockFromStatusTransition("Interviewing")).toBe("interviews");
  });

  it("returns offers for Offered status", () => {
    expect(getUnlockFromStatusTransition("Offered")).toBe("offers");
  });

  it("returns null for other statuses", () => {
    expect(getUnlockFromStatusTransition("Applied")).toBeNull();
    expect(getUnlockFromStatusTransition("Rejected")).toBeNull();
    expect(getUnlockFromStatusTransition("")).toBeNull();
  });
});
