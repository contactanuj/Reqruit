// ApplicationNotes.test.tsx — FE-6.3 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApplicationNotes } from "./ApplicationNotes";
import type { ApplicationNote } from "../types";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const APP_ID = "app-123";

const existingNote: ApplicationNote = {
  id: "note-1",
  application_id: APP_ID,
  content: "Called the recruiter today",
  created_at: "2026-03-01T10:00:00Z",
  updated_at: "2026-03-01T10:00:00Z",
};

const editedNote: ApplicationNote = {
  ...existingNote,
  content: "Updated content",
  updated_at: "2026-03-02T10:00:00Z",
};

const server = setupServer(
  http.get(`http://localhost:8000/applications/${APP_ID}/notes`, () =>
    HttpResponse.json([existingNote])
  ),
  http.post(`http://localhost:8000/applications/${APP_ID}/notes`, async ({ request }) => {
    const body = (await request.json()) as { content: string };
    const newNote: ApplicationNote = {
      id: "note-2",
      application_id: APP_ID,
      content: body.content,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    return HttpResponse.json(newNote);
  }),
  http.patch(
    `http://localhost:8000/applications/${APP_ID}/notes/${existingNote.id}`,
    () => HttpResponse.json(editedNote)
  )
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

function renderNotes() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ApplicationNotes applicationId={APP_ID} />
    </QueryClientProvider>
  );
}

describe("ApplicationNotes (FE-6.3)", () => {
  it("renders existing notes with timestamp", async () => {
    renderNotes();

    await waitFor(() => {
      expect(screen.getByText("Called the recruiter today")).toBeInTheDocument();
    });
  });

  it("adds a new note and shows success toast", async () => {
    const user = userEvent.setup();
    const { toast } = await import("sonner");
    renderNotes();

    // Click Add note
    await waitFor(() => screen.getByLabelText("Add a new note"));
    await user.click(screen.getByLabelText("Add a new note"));

    const textarea = screen.getByLabelText("Note content");
    await user.type(textarea, "My new note text");

    await user.click(screen.getByTestId("save-note-btn"));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Note saved", expect.any(Object));
    });
  });

  it("shows Edited badge when note updated_at differs from created_at", async () => {
    server.use(
      http.get(`http://localhost:8000/applications/${APP_ID}/notes`, () =>
        HttpResponse.json([editedNote])
      )
    );

    renderNotes();

    await waitFor(() => {
      expect(screen.getByTestId("edited-badge")).toBeInTheDocument();
    });
  });

  it("sanitizes XSS content — script tags stripped from note content", async () => {
    const xssNote: ApplicationNote = {
      id: "xss-note",
      application_id: APP_ID,
      content: '<script>alert("xss")</script>Safe content',
      created_at: "2026-03-01T00:00:00Z",
      updated_at: "2026-03-01T00:00:00Z",
    };

    server.use(
      http.get(`http://localhost:8000/applications/${APP_ID}/notes`, () =>
        HttpResponse.json([xssNote])
      )
    );

    renderNotes();

    await waitFor(() => {
      expect(screen.getByText("Safe content")).toBeInTheDocument();
    });

    // Script tag should not be in the DOM
    const scripts = document.querySelectorAll("script");
    const injectedScript = Array.from(scripts).find((s) =>
      s.textContent?.includes("xss")
    );
    expect(injectedScript).toBeUndefined();
  });

  it("saves note with Cmd+Enter keyboard shortcut", async () => {
    const user = userEvent.setup();
    const { toast } = await import("sonner");
    renderNotes();

    await waitFor(() => screen.getByLabelText("Add a new note"));
    await user.click(screen.getByLabelText("Add a new note"));

    const textarea = screen.getByLabelText("Note content");
    await user.type(textarea, "Keyboard shortcut note");
    await user.keyboard("{Meta>}{Enter}{/Meta}");

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Note saved", expect.any(Object));
    });
  });
});
