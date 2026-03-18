// ProfileView.test.tsx — FE-4.3 tests

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { ProfileView } from "./ProfileView";
import type { Profile } from "../types";

expect.extend(toHaveNoViolations);

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/profile",
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockProfile: Profile = {
  id: "user-1",
  contact: {
    name: "Jane Smith",
    email: "jane@example.com",
    phone: "+91 98765 43210",
    location: "Bengaluru, India",
  },
  headline: "Senior Software Engineer",
  summary: "Experienced engineer with 8 years in backend development.",
  experience: [
    {
      id: "exp-1",
      title: "Senior Engineer",
      company: "Acme Corp",
      startDate: "2020-01-01",
      endDate: "2023-12-01",
      description: "Led a team of 5 engineers building microservices.",
    },
    {
      id: "exp-2",
      title: "Software Engineer",
      company: "Beta Ltd",
      startDate: "2017-06-01",
      endDate: "2019-12-01",
    },
  ],
  education: [
    {
      id: "edu-1",
      degree: "B.Tech",
      institution: "IIT Bombay",
      field: "Computer Science",
      startDate: "2013-07-01",
      endDate: "2017-05-01",
    },
  ],
  skills: [
    { id: "s1", name: "Python", category: "Technical" },
    { id: "s2", name: "React", category: "Technical" },
    { id: "s3", name: "Communication", category: "Soft" },
    { id: "s4", name: "Docker", category: "Tools" },
  ],
  targetRoles: ["Backend Engineer"],
  targetCompanies: [],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("ProfileView (FE-4.3)", () => {
  it("renders contact section with name and email", () => {
    render(<ProfileView profile={mockProfile} locale="IN" />);

    expect(screen.getByText("Jane Smith")).toBeInTheDocument();
    expect(screen.getByText("jane@example.com")).toBeInTheDocument();
  });

  it("renders experience items in a list structure", () => {
    render(<ProfileView profile={mockProfile} locale="IN" />);

    const experienceSection = screen.getByRole("region", { name: /work experience/i });
    const list = experienceSection.querySelector("ul");
    expect(list).toBeInTheDocument();

    const items = list?.querySelectorAll("li");
    expect(items?.length).toBe(2);
    expect(screen.getByText("Senior Engineer")).toBeInTheDocument();
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
  });

  it("renders skills grouped by category", () => {
    render(<ProfileView profile={mockProfile} locale="IN" />);

    // Technical skills section should have Python and React
    expect(screen.getByText("Technical")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("React")).toBeInTheDocument();

    // Soft skills
    expect(screen.getByText("Soft")).toBeInTheDocument();
    expect(screen.getByText("Communication")).toBeInTheDocument();

    // Tools
    expect(screen.getByText("Tools")).toBeInTheDocument();
    expect(screen.getByText("Docker")).toBeInTheDocument();
  });

  it("uses semantic section elements with aria-labels", () => {
    render(<ProfileView profile={mockProfile} locale="IN" />);

    expect(screen.getByRole("region", { name: /contact information/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /work experience/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /education/i })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /skills/i })).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<ProfileView profile={mockProfile} locale="IN" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
