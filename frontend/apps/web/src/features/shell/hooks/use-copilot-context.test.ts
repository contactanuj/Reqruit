// use-copilot-context.test.ts — FE-2.6

import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useCopilotContext } from "./use-copilot-context";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

import { usePathname } from "next/navigation";

describe("useCopilotContext", () => {
  it("returns Company Research Analyst for /jobs", () => {
    vi.mocked(usePathname).mockReturnValue("/jobs");
    const { result } = renderHook(() => useCopilotContext());
    expect(result.current.persona).toBe("Company Research Analyst");
  });

  it("returns Negotiation Advisor for /offers", () => {
    vi.mocked(usePathname).mockReturnValue("/offers");
    const { result } = renderHook(() => useCopilotContext());
    expect(result.current.persona).toBe("Negotiation Advisor");
  });

  it("returns Interview Coach for /interviews", () => {
    vi.mocked(usePathname).mockReturnValue("/interviews");
    const { result } = renderHook(() => useCopilotContext());
    expect(result.current.persona).toBe("Interview Coach");
  });

  it("returns Career Advisor for /dashboard", () => {
    vi.mocked(usePathname).mockReturnValue("/dashboard");
    const { result } = renderHook(() => useCopilotContext());
    expect(result.current.persona).toBe("Career Advisor");
  });

  it("returns default for unknown routes", () => {
    vi.mocked(usePathname).mockReturnValue("/unknown");
    const { result } = renderHook(() => useCopilotContext());
    expect(result.current.persona).toBe("Career Advisor");
  });

  it("matches nested routes (e.g. /jobs/123)", () => {
    vi.mocked(usePathname).mockReturnValue("/jobs/some-company");
    const { result } = renderHook(() => useCopilotContext());
    expect(result.current.persona).toBe("Company Research Analyst");
  });
});
