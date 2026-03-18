// WellnessCheckIn.test.tsx — FE-13.2 co-located tests

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WellnessCheckIn } from "./WellnessCheckIn";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockMutate = vi.fn();
let mockIsPending = false;

vi.mock("../hooks/useWellness", () => ({
  useWellnessCheckIn: () => ({
    mutate: mockMutate,
    isPending: mockIsPending,
  }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderComponent() {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <WellnessCheckIn />
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("WellnessCheckIn (FE-13.2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsPending = false;
  });

  it("renders mood radio buttons and energy slider", () => {
    renderComponent();

    expect(screen.getByTestId("wellness-checkin")).toBeInTheDocument();
    expect(screen.getByTestId("mood-1")).toBeInTheDocument();
    expect(screen.getByTestId("mood-2")).toBeInTheDocument();
    expect(screen.getByTestId("mood-3")).toBeInTheDocument();
    expect(screen.getByTestId("mood-4")).toBeInTheDocument();
    expect(screen.getByTestId("mood-5")).toBeInTheDocument();
    expect(screen.getByTestId("energy-slider")).toBeInTheDocument();
    expect(screen.getByTestId("checkin-submit")).toBeInTheDocument();
  });

  it("has correct aria-labels on mood buttons", () => {
    renderComponent();

    expect(screen.getByLabelText("Very unhappy")).toBeInTheDocument();
    expect(screen.getByLabelText("Unhappy")).toBeInTheDocument();
    expect(screen.getByLabelText("Neutral")).toBeInTheDocument();
    expect(screen.getByLabelText("Happy")).toBeInTheDocument();
    expect(screen.getByLabelText("Very happy")).toBeInTheDocument();
  });

  it("disables submit when no mood is selected", () => {
    renderComponent();

    const submit = screen.getByTestId("checkin-submit");
    expect(submit).toBeDisabled();
  });

  it("enables submit when mood is selected", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByTestId("mood-3"));

    const submit = screen.getByTestId("checkin-submit");
    expect(submit).not.toBeDisabled();
  });

  it("calls mutate with mood and energy on submit", async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByTestId("mood-4"));

    // Change energy slider value
    const slider = screen.getByTestId("energy-slider") as HTMLInputElement;
    // Default energy is 3, we submit with the default
    await user.click(screen.getByTestId("checkin-submit"));

    expect(mockMutate).toHaveBeenCalledTimes(1);
    const callArgs = mockMutate.mock.calls[0];
    expect(callArgs[0]).toEqual({ mood: 4, energy: 3 });
  });

  it("shows checked-in state after successful submit", async () => {
    // Make mutate call the onSuccess callback
    mockMutate.mockImplementation((_input: unknown, options: { onSuccess?: () => void }) => {
      options?.onSuccess?.();
    });

    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByTestId("mood-5"));
    await user.click(screen.getByTestId("checkin-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("checked-in-state")).toBeInTheDocument();
    });
    expect(screen.getByText("Checked in today")).toBeInTheDocument();
  });

  it("energy slider has default value of 3", () => {
    renderComponent();

    const slider = screen.getByTestId("energy-slider") as HTMLInputElement;
    expect(slider.value).toBe("3");
  });

  it("energy slider has correct min/max attributes", () => {
    renderComponent();

    const slider = screen.getByTestId("energy-slider") as HTMLInputElement;
    expect(slider.min).toBe("1");
    expect(slider.max).toBe("5");
  });
});
