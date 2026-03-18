// useCoverLetterGeneration.test.ts — FE-7.4, FE-7.5 hook tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useCoverLetterGeneration,
  useApproveCoverLetter,
  useReviseCoverLetter,
  useCoverLetterVersions,
  useDeleteCoverLetterVersion,
} from "./useCoverLetterGeneration";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { useStreamStore } from "@/features/applications/store/stream-store";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

const APP_ID = "app-test-1";

const MOCK_VERSIONS = [
  {
    id: "ver-1",
    version_number: 1,
    generated_at: "2026-03-01T10:00:00Z",
    is_approved: false,
    content: "Cover letter v1",
  },
  {
    id: "ver-2",
    version_number: 2,
    generated_at: "2026-03-10T12:00:00Z",
    is_approved: true,
    content: "Cover letter v2 (approved)",
  },
];

const server = setupServer(
  http.post(`http://localhost:8000/applications/${APP_ID}/cover-letter/generate`, () =>
    HttpResponse.json({ thread_id: "thread-gen-1" })
  ),
  http.post(`http://localhost:8000/applications/${APP_ID}/cover-letter/approve`, () =>
    HttpResponse.json({ id: "cl-1", is_approved: true })
  ),
  http.post(`http://localhost:8000/applications/${APP_ID}/cover-letter/revise`, () =>
    HttpResponse.json({ thread_id: "thread-rev-1" })
  ),
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
  useCreditsStore.setState({ dailyCredits: 5 });
  useStreamStore.getState().reset();
});

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
  return { wrapper: Wrapper, queryClient: qc };
}

// ---------------------------------------------------------------------------
// useCoverLetterGeneration (FE-7.1)
// ---------------------------------------------------------------------------

describe("useCoverLetterGeneration (FE-7.1)", () => {
  it("decrements credits optimistically on mutate", async () => {
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useCoverLetterGeneration(APP_ID), { wrapper });
    useCreditsStore.setState({ dailyCredits: 3 });

    act(() => { result.current.mutate(); });

    // Optimistic decrement happens in onMutate
    expect(useCreditsStore.getState().dailyCredits).toBe(2);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // activeThreadId set in streamStore
    expect(useStreamStore.getState().activeThreadId).toBe("thread-gen-1");
  });

  it("reverts credit on API error", async () => {
    server.use(
      http.post(
        `http://localhost:8000/applications/${APP_ID}/cover-letter/generate`,
        () => HttpResponse.json({}, { status: 500 })
      )
    );
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useCoverLetterGeneration(APP_ID), { wrapper });
    useCreditsStore.setState({ dailyCredits: 3 });

    act(() => { result.current.mutate(); });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(useCreditsStore.getState().dailyCredits).toBe(3);
  });
});

// ---------------------------------------------------------------------------
// useApproveCoverLetter (FE-7.4)
// ---------------------------------------------------------------------------

describe("useApproveCoverLetter (FE-7.4)", () => {
  it("calls POST /cover-letter/approve and succeeds", async () => {
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useApproveCoverLetter(APP_ID), { wrapper });

    act(() => { result.current.mutate(); });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it("returns error state on failure", async () => {
    server.use(
      http.post(
        `http://localhost:8000/applications/${APP_ID}/cover-letter/approve`,
        () => HttpResponse.json({}, { status: 500 })
      )
    );
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useApproveCoverLetter(APP_ID), { wrapper });

    act(() => { result.current.mutate(); });
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ---------------------------------------------------------------------------
// useReviseCoverLetter (FE-7.4)
// ---------------------------------------------------------------------------

describe("useReviseCoverLetter (FE-7.4)", () => {
  it("submits feedback and stores new thread_id", async () => {
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useReviseCoverLetter(APP_ID), { wrapper });

    act(() => {
      result.current.mutate({ feedback: "Make it more concise" });
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(useStreamStore.getState().activeThreadId).toBe("thread-rev-1");
  });
});

// ---------------------------------------------------------------------------
// useCoverLetterVersions (FE-7.5)
// ---------------------------------------------------------------------------

describe("useCoverLetterVersions (FE-7.5)", () => {
  it("fetches and returns all versions", async () => {
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useCoverLetterVersions(APP_ID), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(2);
    expect(result.current.data?.[0].version_number).toBe(1);
    expect(result.current.data?.[1].is_approved).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// useDeleteCoverLetterVersion (FE-7.5)
// ---------------------------------------------------------------------------

describe("useDeleteCoverLetterVersion (FE-7.5)", () => {
  it("deletes a version by id", async () => {
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useDeleteCoverLetterVersion(APP_ID), {
      wrapper,
    });

    act(() => { result.current.mutate("ver-1"); });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it("shows error toast on delete failure", async () => {
    server.use(
      http.delete(
        `http://localhost:8000/applications/${APP_ID}/cover-letters/ver-1`,
        () => HttpResponse.json({}, { status: 500 })
      )
    );
    const { toast } = await import("sonner");
    const { wrapper } = makeWrapper();
    const { result } = renderHook(() => useDeleteCoverLetterVersion(APP_ID), {
      wrapper,
    });

    act(() => { result.current.mutate("ver-1"); });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).toHaveBeenCalled();
  });
});
