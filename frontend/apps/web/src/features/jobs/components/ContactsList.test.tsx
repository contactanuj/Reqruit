// ContactsList.test.tsx — FE-5.7 tests

import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ContactsList } from "./ContactsList";
import type { Contact } from "../types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

const mockContacts: Contact[] = [
  {
    id: "c1",
    name: "Jane Smith",
    role_type: "Recruiter",
    linkedin_url: "https://linkedin.com/in/janesmith",
    email: "jane@example.com",
  },
  {
    id: "c2",
    name: "Bob Dev",
    role_type: "Engineer",
  },
];

let contactsData: Contact[] = [...mockContacts];

const server = setupServer(
  http.get("http://localhost:8000/jobs/:jobId/contacts", () =>
    HttpResponse.json(contactsData)
  ),
  http.post("http://localhost:8000/jobs/:jobId/contacts", async ({ request }) => {
    const body = (await request.json()) as Contact;
    const newContact: Contact = {
      id: "c-new",
      name: body.name,
      role_type: body.role_type ?? "Generic",
    };
    contactsData.push(newContact);
    return HttpResponse.json(newContact);
  }),
  http.delete("http://localhost:8000/jobs/:jobId/contacts/:contactId", ({ params }) => {
    const { contactId } = params;
    contactsData = contactsData.filter((c) => c.id !== contactId);
    return new HttpResponse(null, { status: 204 });
  })
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterAll(() => server.close());
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
  contactsData = [...mockContacts];
});

function renderComponent(jobId = "job-1") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <ContactsList jobId={jobId} />
    </QueryClientProvider>
  );
}

describe("ContactsList (FE-5.7)", () => {
  it("renders existing contacts with name, role type, and LinkedIn", async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("Jane Smith")).toBeInTheDocument();
      expect(screen.getByText("Recruiter")).toBeInTheDocument();
      expect(screen.getByText("LinkedIn")).toBeInTheDocument();
      expect(screen.getByText("Bob Dev")).toBeInTheDocument();
      expect(screen.getByText("Engineer")).toBeInTheDocument();
    });
  });

  it("shows add contact form when clicking add button", async () => {
    const user = userEvent.setup();
    renderComponent();

    await waitFor(() => screen.getByText("Jane Smith"));
    await user.click(screen.getByText(/\+ Add contact/i));

    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/role type/i)).toBeInTheDocument();
  });

  it("shows delete confirmation dialog on delete click", async () => {
    const user = userEvent.setup();
    renderComponent();

    await waitFor(() => screen.getByText("Jane Smith"));
    await user.click(screen.getByLabelText("Delete contact Jane Smith"));

    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    expect(screen.getByText(/Delete this contact\?/i)).toBeInTheDocument();
  });

  it("removes contact after confirming delete", async () => {
    const user = userEvent.setup();
    renderComponent();

    await waitFor(() => screen.getByText("Jane Smith"));
    await user.click(screen.getByLabelText("Delete contact Jane Smith"));
    await user.click(screen.getByRole("button", { name: /^delete$/i }));

    await waitFor(() => {
      expect(screen.queryByText("Jane Smith")).not.toBeInTheDocument();
    });
  });
});
