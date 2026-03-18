// TaskQueueTable.test.tsx — FE-15.3 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TaskQueueTable } from "./TaskQueueTable";
import type { BackgroundTask } from "../types";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

// Mock useFocusTrap to avoid DOM focus issues in test
vi.mock("@repo/ui/hooks", () => ({
  useFocusTrap: ({ open, onClose }: { open: boolean; onClose: () => void }) => ({
    dialogRef: { current: null },
    handleBackdropClick: (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) onClose();
    },
  }),
}));

const mockTasks: BackgroundTask[] = [
  { id: "task-1", type: "resume_parse", status: "failed", createdAt: "2026-03-17T10:00:00Z" },
  { id: "task-2", type: "sync_jobs", status: "pending", createdAt: "2026-03-17T11:00:00Z" },
  { id: "task-3", type: "email_send", status: "running", createdAt: "2026-03-17T12:00:00Z" },
  { id: "task-4", type: "report_gen", status: "completed", createdAt: "2026-03-17T09:00:00Z" },
];

const server = setupServer(
  http.get("http://localhost:8000/admin/tasks", () =>
    HttpResponse.json(mockTasks),
  ),
  http.post("http://localhost:8000/admin/tasks/:id/retry", () =>
    HttpResponse.json(null, { status: 200 }),
  ),
  http.delete("http://localhost:8000/admin/tasks/:id", () =>
    HttpResponse.json(null, { status: 204 }),
  ),
  http.get("http://localhost:8000/admin/tasks/:id/logs", () =>
    HttpResponse.json("Log line 1\nLog line 2\nLog line 3"),
  ),
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
      <TaskQueueTable />
    </QueryClientProvider>,
  );
}

describe("TaskQueueTable (FE-15.3)", () => {
  it("renders task rows with correct statuses", async () => {
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("task-queue-table")).toBeInTheDocument();
    });

    expect(screen.getByTestId("task-row-task-1")).toBeInTheDocument();
    expect(screen.getByTestId("task-row-task-2")).toBeInTheDocument();
    expect(screen.getByTestId("task-row-task-3")).toBeInTheDocument();
    expect(screen.getByTestId("task-row-task-4")).toBeInTheDocument();
  });

  it("shows Retry button only for failed tasks", async () => {
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("task-queue-table")).toBeInTheDocument();
    });

    // Failed task has retry button
    expect(screen.getByTestId("retry-button-task-1")).toBeInTheDocument();

    // Others do not
    expect(screen.queryByTestId("retry-button-task-2")).not.toBeInTheDocument();
    expect(screen.queryByTestId("retry-button-task-3")).not.toBeInTheDocument();
    expect(screen.queryByTestId("retry-button-task-4")).not.toBeInTheDocument();
  });

  it("shows Cancel button only for pending tasks", async () => {
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("task-queue-table")).toBeInTheDocument();
    });

    // Pending task has cancel button
    expect(screen.getByTestId("cancel-button-task-2")).toBeInTheDocument();

    // Others do not
    expect(screen.queryByTestId("cancel-button-task-1")).not.toBeInTheDocument();
    expect(screen.queryByTestId("cancel-button-task-3")).not.toBeInTheDocument();
    expect(screen.queryByTestId("cancel-button-task-4")).not.toBeInTheDocument();
  });

  it("Cancel button uses window.confirm before proceeding", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("cancel-button-task-2")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("cancel-button-task-2"));

    expect(confirmSpy).toHaveBeenCalledWith(
      "Are you sure you want to cancel this task? This action cannot be undone.",
    );

    // Task should still be visible (confirm returned false)
    expect(screen.getByTestId("task-row-task-2")).toBeInTheDocument();

    confirmSpy.mockRestore();
  });

  it("Cancel proceeds when window.confirm returns true", async () => {
    let deleteCalled = false;
    server.use(
      http.delete("http://localhost:8000/admin/tasks/:id", () => {
        deleteCalled = true;
        return HttpResponse.json(null, { status: 204 });
      }),
      http.get("http://localhost:8000/admin/tasks", () => {
        // After DELETE, return list without the cancelled task
        if (deleteCalled) {
          return HttpResponse.json(mockTasks.filter((t) => t.id !== "task-2"));
        }
        return HttpResponse.json(mockTasks);
      }),
    );

    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("cancel-button-task-2")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("cancel-button-task-2"));

    expect(confirmSpy).toHaveBeenCalled();

    // Optimistic removal: task-2 should disappear
    await waitFor(() => {
      expect(screen.queryByTestId("task-row-task-2")).not.toBeInTheDocument();
    });

    confirmSpy.mockRestore();
  });

  it("Retry button triggers retry mutation", async () => {
    let retryCalled = false;
    server.use(
      http.post("http://localhost:8000/admin/tasks/:id/retry", () => {
        retryCalled = true;
        return HttpResponse.json(null, { status: 200 });
      }),
      http.get("http://localhost:8000/admin/tasks", () => {
        // After retry, return list with updated status
        if (retryCalled) {
          return HttpResponse.json(
            mockTasks.map((t) =>
              t.id === "task-1" ? { ...t, status: "pending" } : t,
            ),
          );
        }
        return HttpResponse.json(mockTasks);
      }),
    );

    const user = userEvent.setup();
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("retry-button-task-1")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("retry-button-task-1"));

    // Optimistic update changes status to pending, so retry button should disappear
    await waitFor(() => {
      expect(screen.queryByTestId("retry-button-task-1")).not.toBeInTheDocument();
    });
  });

  it("View Logs button is present for all tasks", async () => {
    renderTable();

    await waitFor(() => {
      expect(screen.getByTestId("task-queue-table")).toBeInTheDocument();
    });

    expect(screen.getByTestId("view-logs-task-1")).toBeInTheDocument();
    expect(screen.getByTestId("view-logs-task-2")).toBeInTheDocument();
    expect(screen.getByTestId("view-logs-task-3")).toBeInTheDocument();
    expect(screen.getByTestId("view-logs-task-4")).toBeInTheDocument();
  });

  it("shows skeleton while loading", () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <TaskQueueTable />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("task-queue-skeleton")).toBeInTheDocument();
  });
});
