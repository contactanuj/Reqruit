// LocaleConfigTable.test.tsx — FE-15.1 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LocaleConfigTable } from "./LocaleConfigTable";
import type { LocaleConfig } from "../types";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const mockConfigs: LocaleConfig[] = [
  {
    locale: "en-US",
    currencySymbol: "$",
    salaryRangeMin: 30000,
    salaryRangeMax: 300000,
    jobBoardSources: ["LinkedIn", "Indeed"],
    noticePeriodDefault: 14,
  },
  {
    locale: "en-GB",
    currencySymbol: "£",
    salaryRangeMin: 25000,
    salaryRangeMax: 200000,
    jobBoardSources: ["Reed", "Totaljobs"],
    noticePeriodDefault: 30,
  },
];

const server = setupServer(
  http.get("http://localhost:8000/admin/locale-config", () =>
    HttpResponse.json(mockConfigs),
  ),
  http.patch("http://localhost:8000/admin/locale-config/:locale", async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ ...mockConfigs[0], ...(body as Record<string, unknown>) });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

function renderTable() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <LocaleConfigTable />
    </QueryClientProvider>,
  );
}

describe("LocaleConfigTable (FE-15.1)", () => {
  it("renders rows for each locale config", async () => {
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("locale-config-table")).toBeInTheDocument();
    });

    expect(screen.getByTestId("locale-row-en-US")).toBeInTheDocument();
    expect(screen.getByTestId("locale-row-en-GB")).toBeInTheDocument();
    expect(screen.getByText("$")).toBeInTheDocument();
    expect(screen.getByText("£")).toBeInTheDocument();
  });

  it("enters inline edit mode on Edit click and shows Save/Cancel", async () => {
    const user = userEvent.setup();
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("edit-button-en-US")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("edit-button-en-US"));

    expect(screen.getByTestId("save-button-en-US")).toBeInTheDocument();
    expect(screen.getByTestId("cancel-button-en-US")).toBeInTheDocument();
    expect(screen.getByTestId("edit-currency-en-US")).toBeInTheDocument();
  });

  it("cancels edit and returns to display mode", async () => {
    const user = userEvent.setup();
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("edit-button-en-US")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("edit-button-en-US"));
    expect(screen.getByTestId("save-button-en-US")).toBeInTheDocument();

    await user.click(screen.getByTestId("cancel-button-en-US"));

    expect(screen.getByTestId("edit-button-en-US")).toBeInTheDocument();
    expect(screen.queryByTestId("save-button-en-US")).not.toBeInTheDocument();
  });

  it("saves edited values via PATCH", async () => {
    const user = userEvent.setup();
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("edit-button-en-US")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("edit-button-en-US"));

    const currencyInput = screen.getByTestId("edit-currency-en-US");
    await user.clear(currencyInput);
    await user.type(currencyInput, "EUR");

    await user.click(screen.getByTestId("save-button-en-US"));

    // After successful mutation, edit mode should close
    await waitFor(() => {
      expect(screen.getByTestId("edit-button-en-US")).toBeInTheDocument();
    });
  });

  it("disables other Edit buttons while one row is in edit mode", async () => {
    const user = userEvent.setup();
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("edit-button-en-US")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("edit-button-en-US"));

    expect(screen.getByTestId("edit-button-en-GB")).toBeDisabled();
  });

  it("shows skeleton while loading", () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <LocaleConfigTable />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("locale-config-skeleton")).toBeInTheDocument();
  });
});
