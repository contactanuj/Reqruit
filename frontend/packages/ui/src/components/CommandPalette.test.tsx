// CommandPalette.test.tsx — FE-2.3 (AC: #1, #2, #4)

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CommandPalette } from "./CommandPalette";
import type { CommandItem } from "./CommandPalette";

const mockItems: CommandItem[] = [
  {
    id: "nav-dashboard",
    label: "Dashboard",
    category: "navigation",
    action: vi.fn(),
  },
  {
    id: "nav-jobs",
    label: "Jobs",
    category: "navigation",
    action: vi.fn(),
  },
  {
    id: "ai-cover",
    label: "Generate cover letter",
    category: "ai-action",
    action: vi.fn(),
  },
];

beforeEach(() => {
  // Provide matchMedia stub for jsdom
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
});

describe("CommandPalette", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <CommandPalette open={false} onClose={vi.fn()} items={mockItems} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders search input when open", () => {
    render(
      <CommandPalette open={true} onClose={vi.fn()} items={mockItems} />,
    );
    const input = screen.getByRole("combobox", { name: /search commands/i });
    expect(input).toBeTruthy();
  });

  it("focuses search input when opened", () => {
    render(
      <CommandPalette open={true} onClose={vi.fn()} items={mockItems} />,
    );
    const input = screen.getByRole("combobox");
    expect(document.activeElement).toBe(input);
  });

  it("filters results as user types", () => {
    render(
      <CommandPalette open={true} onClose={vi.fn()} items={mockItems} />,
    );
    const input = screen.getByRole("combobox");
    fireEvent.change(input, { target: { value: "job" } });
    expect(screen.getByText("Jobs")).toBeTruthy();
    expect(screen.queryByText("Dashboard")).toBeNull();
  });

  it("calls onClose when Escape is pressed", () => {
    const onClose = vi.fn();
    render(
      <CommandPalette open={true} onClose={onClose} items={mockItems} />,
    );
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls item action and onClose when result is clicked", () => {
    const onClose = vi.fn();
    const action = vi.fn();
    const items: CommandItem[] = [
      { id: "t1", label: "Test Item", category: "navigation", action },
    ];
    render(<CommandPalette open={true} onClose={onClose} items={items} />);
    fireEvent.click(screen.getByText("Test Item"));
    expect(action).toHaveBeenCalledOnce();
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("has role=dialog with correct aria-label", () => {
    render(
      <CommandPalette open={true} onClose={vi.fn()} items={mockItems} />,
    );
    const dialog = screen.getByRole("dialog", { name: /command palette/i });
    expect(dialog).toBeTruthy();
  });
});
