import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { OfflineBanner } from "./OfflineBanner";

describe("OfflineBanner", () => {
  // Store original navigator.onLine descriptor
  const originalOnLine = Object.getOwnPropertyDescriptor(navigator, "onLine");

  function setOnline(value: boolean) {
    Object.defineProperty(navigator, "onLine", {
      writable: true,
      configurable: true,
      value,
    });
  }

  afterEach(() => {
    // Restore
    if (originalOnLine) {
      Object.defineProperty(navigator, "onLine", originalOnLine);
    } else {
      Object.defineProperty(navigator, "onLine", {
        writable: true,
        configurable: true,
        value: true,
      });
    }
  });

  beforeEach(() => {
    setOnline(true);
  });

  it("does not render when online", () => {
    setOnline(true);
    render(<OfflineBanner />);
    expect(screen.queryByTestId("offline-banner")).not.toBeInTheDocument();
  });

  it("renders when offline on mount", () => {
    setOnline(false);
    render(<OfflineBanner />);
    expect(screen.getByTestId("offline-banner")).toBeInTheDocument();
  });

  it("has role=alert for screen reader announcement", () => {
    setOnline(false);
    render(<OfflineBanner />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("shows 'You're offline — showing cached data' message", () => {
    setOnline(false);
    render(<OfflineBanner />);
    expect(
      screen.getByText("You're offline — showing cached data")
    ).toBeInTheDocument();
  });

  it("banner appears when offline event fires", () => {
    setOnline(true);
    render(<OfflineBanner />);
    expect(screen.queryByTestId("offline-banner")).not.toBeInTheDocument();

    act(() => {
      setOnline(false);
      window.dispatchEvent(new Event("offline"));
    });

    expect(screen.getByTestId("offline-banner")).toBeInTheDocument();
  });

  it("banner dismisses when online event fires", () => {
    setOnline(false);
    render(<OfflineBanner />);
    expect(screen.getByTestId("offline-banner")).toBeInTheDocument();

    act(() => {
      setOnline(true);
      window.dispatchEvent(new Event("online"));
    });

    expect(screen.queryByTestId("offline-banner")).not.toBeInTheDocument();
  });
});
