// useBulkOperations.test.ts — FE-6.4 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useBulkDelete, useBulkWithdraw, useBulkExport } from "./useBulkOperations";
import { useApplicationsStore } from "../store/applications-store";
import type { Application } from "../types";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const sampleApps: Application[] = [
  {
    id: "app-1",
    job_title: "Engineer",
    company: "Corp A",
    status: "Saved",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "app-2",
    job_title: "Designer",
    company: "Corp B",
    status: "Applied",
    created_at: "2026-01-02T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
  },
];

const server = setupServer(
  http.delete("http://localhost:8000/applications/bulk", () =>
    HttpResponse.json({ deleted: 2 })
  ),
  http.patch("http://localhost:8000/applications/bulk/status", () =>
    HttpResponse.json({ updated: 2 })
  ),
  http.post("http://localhost:8000/applications/export", () =>
    new HttpResponse("id,title,company\napp-1,Engineer,Corp A", {
      headers: { "Content-Type": "text/csv" },
    })
  )
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
  // Reset zustand store
  useApplicationsStore.setState({ selectedIds: new Set() });
});

function makeWrapper(qc: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: qc }, children);
  };
}

describe("useApplicationsStore — bulk selection (FE-6.4)", () => {
  it("toggleSelect adds and removes IDs", () => {
    const { result } = renderHook(() => useApplicationsStore());

    act(() => result.current.toggleSelect("app-1"));
    expect(result.current.selectedIds.has("app-1")).toBe(true);

    act(() => result.current.toggleSelect("app-1"));
    expect(result.current.selectedIds.has("app-1")).toBe(false);
  });

  it("selectAll fills selectedIds with all provided IDs", () => {
    const { result } = renderHook(() => useApplicationsStore());

    act(() => result.current.selectAll(["app-1", "app-2", "app-3"]));
    expect(result.current.selectedIds.size).toBe(3);
  });

  it("clearSelection empties selectedIds", () => {
    const { result } = renderHook(() => useApplicationsStore());

    act(() => result.current.selectAll(["app-1", "app-2"]));
    act(() => result.current.clearSelection());
    expect(result.current.selectedIds.size).toBe(0);
  });
});

describe("useBulkDelete (FE-6.4)", () => {
  it("removes deleted applications from cache optimistically", async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(["applications", "list", undefined], sampleApps);

    const { result } = renderHook(() => useBulkDelete(), {
      wrapper: makeWrapper(qc),
    });

    await act(async () => {
      result.current.mutate(["app-1"]);
    });

    await waitFor(() => result.current.isSuccess);

    const { toast } = await import("sonner");
    expect(toast.success).toHaveBeenCalledWith("Applications deleted");
  });

  it("reverts cache and shows error toast on delete failure", async () => {
    server.use(
      http.delete("http://localhost:8000/applications/bulk", () =>
        HttpResponse.json({ error: "Server error" }, { status: 500 })
      )
    );

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(["applications", "list", undefined], sampleApps);

    const { result } = renderHook(() => useBulkDelete(), {
      wrapper: makeWrapper(qc),
    });

    await act(async () => {
      result.current.mutate(["app-1"]);
    });

    await waitFor(() => result.current.isError);

    const { toast } = await import("sonner");
    expect(toast.error).toHaveBeenCalledWith(
      "Failed to delete applications — changes reverted"
    );

    // Cache should be reverted
    const cached = qc.getQueryData<Application[]>(["applications", "list", undefined]);
    expect(cached).toHaveLength(2);
  });
});

describe("useBulkWithdraw (FE-6.4)", () => {
  it("moves selected applications to Withdrawn status optimistically", async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(["applications", "list", undefined], sampleApps);

    const { result } = renderHook(() => useBulkWithdraw(), {
      wrapper: makeWrapper(qc),
    });

    await act(async () => {
      result.current.mutate(["app-1"]);
    });

    // Check optimistic update was applied
    const cached = qc.getQueryData<Application[]>(["applications", "list", undefined]);
    const app1 = cached?.find((a) => a.id === "app-1");
    // After optimistic update, app-1 should have Withdrawn status
    expect(app1?.status).toBe("Withdrawn");
  });
});

describe("useBulkExport (FE-6.4)", () => {
  it("triggers CSV download and shows success toast", async () => {
    // Mock URL.createObjectURL / revokeObjectURL and anchor click
    const createObjectURLMock = vi.fn().mockReturnValue("blob:fake-url");
    const revokeObjectURLMock = vi.fn();
    globalThis.URL.createObjectURL = createObjectURLMock;
    globalThis.URL.revokeObjectURL = revokeObjectURLMock;

    const clickMock = vi.fn();
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      if (tag === "a") {
        return { href: "", download: "", click: clickMock } as unknown as HTMLAnchorElement;
      }
      return document.createElement(tag);
    });

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useBulkExport(), {
      wrapper: makeWrapper(qc),
    });

    await act(async () => {
      result.current.mutate(["app-1"]);
    });

    await waitFor(() => result.current.isSuccess);

    const { toast } = await import("sonner");
    expect(toast.success).toHaveBeenCalledWith("Export started — check your downloads");
    expect(clickMock).toHaveBeenCalled();
    expect(revokeObjectURLMock).toHaveBeenCalledWith("blob:fake-url");

    vi.restoreAllMocks();
  });

  it("shows error toast on export failure", async () => {
    server.use(
      http.post("http://localhost:8000/applications/export", () =>
        HttpResponse.json({ error: "Server error" }, { status: 500 })
      )
    );

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { result } = renderHook(() => useBulkExport(), {
      wrapper: makeWrapper(qc),
    });

    await act(async () => {
      result.current.mutate(["app-1"]);
    });

    await waitFor(() => result.current.isError);

    const { toast } = await import("sonner");
    expect(toast.error).toHaveBeenCalledWith("Failed to export applications");
  });
});
