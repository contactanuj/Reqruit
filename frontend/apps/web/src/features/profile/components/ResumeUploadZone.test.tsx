// ResumeUploadZone.test.tsx — FE-4.1 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ResumeUploadZone } from "./ResumeUploadZone";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/profile",
}));

// ---------------------------------------------------------------------------
// MSW server
// ---------------------------------------------------------------------------

const handlers = [
  http.post("http://localhost:8000/resumes/upload", async () => {
    return HttpResponse.json({
      id: "resume-123",
      filename: "my-resume.pdf",
      parseStatus: "pending",
    });
  }),
];

const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function renderComponent(onUploadSuccess?: (resumeId: string) => void) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <ResumeUploadZone onUploadSuccess={onUploadSuccess} />
    </QueryClientProvider>
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ResumeUploadZone (FE-4.1)", () => {
  it("renders upload zone with correct aria-label", () => {
    renderComponent();
    expect(
      screen.getByRole("button", { name: /upload resume/i })
    ).toBeInTheDocument();
  });

  it("accepts a valid PDF file and calls upload", async () => {
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    renderComponent(onSuccess);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["pdf content"], "resume.pdf", { type: "application/pdf" });
    await user.upload(input, file);

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith("resume-123");
    });
  });

  it("rejects a .txt file with inline error", () => {
    renderComponent();

    // Use fireEvent to bypass the accept attribute filtering in jsdom
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["text content"], "resume.txt", { type: "text/plain" });
    Object.defineProperty(input, "files", {
      value: [file],
      writable: false,
    });
    fireEvent.change(input);

    expect(screen.getByRole("alert")).toHaveTextContent(
      /only pdf and docx files are supported/i
    );
  });

  it("rejects a file larger than 10MB", async () => {
    const user = userEvent.setup();
    renderComponent();

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    // Create a mock 11MB file
    const bigContent = "x".repeat(11 * 1024 * 1024);
    const file = new File([bigContent], "huge.pdf", { type: "application/pdf" });
    await user.upload(input, file);

    expect(screen.getByRole("alert")).toHaveTextContent(
      /file must be 10mb or smaller/i
    );
  });

  it("accepts a valid DOCX file and calls upload", async () => {
    const onSuccess = vi.fn();
    const user = userEvent.setup();
    renderComponent(onSuccess);

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["docx content"], "resume.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    await user.upload(input, file);

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith("resume-123");
    });
  });
});
