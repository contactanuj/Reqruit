// DocumentVersionList.test.tsx — FE-7.5 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DocumentVersionList } from "./DocumentVersionList";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const APP_ID = "app-docs-1";

const MOCK_VERSIONS = [
  {
    id: "ver-1",
    version_number: 1,
    generated_at: "2026-03-01T10:00:00Z",
    is_approved: false,
    content: "Cover letter version one content here.",
  },
  {
    id: "ver-2",
    version_number: 2,
    generated_at: "2026-03-10T12:00:00Z",
    is_approved: true,
    content: "Cover letter version two content here (approved).",
  },
];

const server = setupServer(
  http.get(`http://localhost:8000/applications/${APP_ID}/cover-letters`, () =>
    HttpResponse.json(MOCK_VERSIONS)
  ),
  http.delete(
    `http://localhost:8000/applications/${APP_ID}/cover-letters/ver-1`,
    () => new HttpResponse(null, { status: 204 })
  )
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderList() {
  const qc = makeQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <DocumentVersionList applicationId={APP_ID} locale="en-US" />
    </QueryClientProvider>
  );
}

describe("DocumentVersionList (FE-7.5)", () => {
  it("renders version list with version numbers and dates", async () => {
    renderList();
    await waitFor(() =>
      expect(screen.getByTestId("version-list")).toBeInTheDocument()
    );
    expect(screen.getByText("v1")).toBeInTheDocument();
    expect(screen.getByText("v2")).toBeInTheDocument();
  });

  it("shows Active badge for approved version", async () => {
    renderList();
    await waitFor(() =>
      expect(screen.getAllByTestId("active-badge")).toHaveLength(1)
    );
    expect(screen.getByTestId("active-badge")).toHaveTextContent("Active");
  });

  it("renders View, Download, Delete buttons for each version", async () => {
    renderList();
    await waitFor(() =>
      expect(screen.getByTestId("version-list")).toBeInTheDocument()
    );
    expect(screen.getByTestId("view-button-ver-1")).toBeInTheDocument();
    expect(screen.getByTestId("download-button-ver-1")).toBeInTheDocument();
    expect(screen.getByTestId("delete-button-ver-1")).toBeInTheDocument();
  });

  it("clicking View opens full-screen modal with cover letter text", async () => {
    const user = userEvent.setup();
    renderList();
    await waitFor(() =>
      expect(screen.getByTestId("view-button-ver-1")).toBeInTheDocument()
    );
    await user.click(screen.getByTestId("view-button-ver-1"));
    expect(screen.getByTestId("view-version-modal")).toBeInTheDocument();
    expect(screen.getByTestId("version-content")).toHaveTextContent(
      "Cover letter version one content here."
    );
  });

  it("closes the view modal when close button is clicked", async () => {
    const user = userEvent.setup();
    renderList();
    await waitFor(() =>
      expect(screen.getByTestId("view-button-ver-1")).toBeInTheDocument()
    );
    await user.click(screen.getByTestId("view-button-ver-1"));
    expect(screen.getByTestId("view-version-modal")).toBeInTheDocument();
    await user.click(screen.getByTestId("close-view-modal"));
    expect(screen.queryByTestId("view-version-modal")).not.toBeInTheDocument();
  });

  it("clicking Delete on non-approved version shows AlertDialog", async () => {
    const user = userEvent.setup();
    renderList();
    await waitFor(() =>
      expect(screen.getByTestId("delete-button-ver-1")).toBeInTheDocument()
    );
    await user.click(screen.getByTestId("delete-button-ver-1"));
    expect(screen.getByTestId("confirm-delete-dialog")).toBeInTheDocument();
    expect(screen.getByTestId("confirm-delete-dialog")).toHaveTextContent(
      "Delete this version?"
    );
  });

  it("confirms delete removes version from list", async () => {
    const user = userEvent.setup();
    renderList();
    await waitFor(() =>
      expect(screen.getByTestId("delete-button-ver-1")).toBeInTheDocument()
    );
    await user.click(screen.getByTestId("delete-button-ver-1"));
    await user.click(screen.getByTestId("confirm-delete-button"));
    await waitFor(() =>
      expect(screen.queryByTestId("confirm-delete-dialog")).not.toBeInTheDocument()
    );
  });

  it("clicking Delete on approved version shows inline blocked message", async () => {
    const user = userEvent.setup();
    renderList();
    await waitFor(() =>
      expect(screen.getByTestId("delete-button-ver-2")).toBeInTheDocument()
    );
    await user.click(screen.getByTestId("delete-button-ver-2"));
    // No AlertDialog — instead inline error
    expect(screen.queryByTestId("confirm-delete-dialog")).not.toBeInTheDocument();
    expect(screen.getByTestId("active-delete-error")).toHaveTextContent(
      "Cannot delete the active cover letter"
    );
  });

  it("shows empty state when no versions exist", async () => {
    server.use(
      http.get(
        `http://localhost:8000/applications/${APP_ID}/cover-letters`,
        () => HttpResponse.json([])
      )
    );
    renderList();
    await waitFor(() =>
      expect(
        screen.getByText("No cover letters generated yet.")
      ).toBeInTheDocument()
    );
  });
});
