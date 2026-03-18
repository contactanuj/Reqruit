// StatusTransitionGuard.test.tsx — FE-6.2 tests

import { describe, it, expect, vi, afterEach } from "vitest";
import { toast } from "sonner";
import { guardStatusTransition } from "./StatusTransitionGuard";
import { isValidTransition, VALID_TRANSITIONS } from "../types";
import type { ApplicationStatus } from "../types";

vi.mock("sonner", () => ({
  toast: {
    warning: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
  },
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("StatusTransitionGuard (FE-6.2)", () => {
  it("blocks invalid transition Saved → Offered and shows persistent toast", () => {
    const result = guardStatusTransition("Saved", "Offered");

    expect(result).toBe(false);
    expect(toast.warning).toHaveBeenCalledOnce();

    const [message, options] = vi.mocked(toast.warning).mock.calls[0] as [string, Record<string, unknown>];
    expect(message).toContain("Cannot move directly from Saved to Offered");
    // Persistent toast: duration must be Infinity (UX-17)
    expect(options.duration).toBe(Infinity);
    // Must have "Got it" dismiss action
    expect((options.action as { label: string }).label).toBe("Got it");
  });

  it("allows valid transition Saved → Applied (no toast shown)", () => {
    const result = guardStatusTransition("Saved", "Applied");

    expect(result).toBe(true);
    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("shows toast with dismiss button for any blocked transition", () => {
    guardStatusTransition("Interviewing", "Accepted");

    expect(toast.warning).toHaveBeenCalledOnce();
    const [, options] = vi.mocked(toast.warning).mock.calls[0] as [string, Record<string, unknown>];
    const action = options.action as { label: string };
    expect(action.label).toBe("Got it");
  });
});

describe("VALID_TRANSITIONS matrix (FE-6.2)", () => {
  const terminalStates: ApplicationStatus[] = ["Accepted", "Rejected", "Withdrawn"];
  const allStatuses = Object.keys(VALID_TRANSITIONS) as ApplicationStatus[];

  it("terminal states have no valid outgoing transitions", () => {
    for (const terminal of terminalStates) {
      expect(VALID_TRANSITIONS[terminal]).toHaveLength(0);
    }
  });

  it("Saved can only go to Applied or Withdrawn", () => {
    expect(VALID_TRANSITIONS["Saved"]).toContain("Applied");
    expect(VALID_TRANSITIONS["Saved"]).toContain("Withdrawn");
    expect(VALID_TRANSITIONS["Saved"]).not.toContain("Offered");
    expect(VALID_TRANSITIONS["Saved"]).not.toContain("Accepted");
  });

  it("isValidTransition returns false for all terminal → any transitions", () => {
    for (const terminal of terminalStates) {
      for (const status of allStatuses) {
        if (status !== terminal) {
          expect(isValidTransition(terminal, status)).toBe(false);
        }
      }
    }
  });
});
