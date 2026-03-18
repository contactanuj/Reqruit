"use client";

// ProfileView.tsx — FE-4.3: Structured profile display

import type { ReactNode } from "react";
import { formatDate } from "@repo/ui/lib/locale";
import type { LocaleCode } from "@repo/ui/lib/locale";
import type { Profile, Skill, SkillCategory } from "../types";

interface ProfileViewProps {
  profile: Profile;
  locale: LocaleCode;
}

type SkillGroupKey = SkillCategory | "Other";
const SKILL_CATEGORY_ORDER: SkillGroupKey[] = ["Technical", "Soft", "Tools", "Other"];

function groupSkills(skills: Skill[]): Record<SkillGroupKey, Skill[]> {
  const grouped: Record<SkillGroupKey, Skill[]> = {
    Technical: [],
    Soft: [],
    Tools: [],
    Other: [],
  };
  for (const skill of skills) {
    if (grouped[skill.category]) {
      grouped[skill.category].push(skill);
    } else {
      grouped.Other.push(skill);
    }
  }
  return grouped;
}

function safeFormatDate(date: string | undefined | null, locale: LocaleCode): string {
  if (!date || !date.trim()) return "";
  try {
    return formatDate(date, locale);
  } catch {
    return date;
  }
}

function formatDateRange(
  startDate: string,
  endDate: string | null | undefined,
  locale: LocaleCode
): string {
  const start = safeFormatDate(startDate, locale);
  if (!start) return "";
  if (!endDate) return `${start} – Present`;
  const end = safeFormatDate(endDate, locale);
  return end ? `${start} – ${end}` : `${start} – Present`;
}

function Badge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-border bg-secondary px-2.5 py-0.5 text-xs font-semibold text-secondary-foreground transition-colors">
      {children}
    </span>
  );
}

export function ProfileView({ profile, locale }: ProfileViewProps) {
  const groupedSkills = groupSkills(profile.skills);

  return (
    <div className="flex flex-col gap-8">
      {/* Contact Information */}
      <section aria-label="Contact information">
        <h2 className="text-xl font-bold">{profile.contact.name}</h2>
        {profile.headline && (
          <p className="mt-1 text-base text-muted-foreground">{profile.headline}</p>
        )}
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
          <span>{profile.contact.email}</span>
          {profile.contact.phone && <span>{profile.contact.phone}</span>}
          {profile.contact.location && <span>{profile.contact.location}</span>}
        </div>
      </section>

      {/* Professional Summary */}
      {profile.summary && (
        <section aria-label="Professional summary">
          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Summary
          </h3>
          <p className="text-sm leading-relaxed">{profile.summary}</p>
        </section>
      )}

      {/* Work Experience */}
      {profile.experience.length > 0 && (
        <section aria-label="Work experience">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Experience
          </h3>
          <ul className="flex flex-col gap-4">
            {profile.experience.map((exp) => (
              <li key={exp.id} className="border-l-2 border-border pl-4">
                <div className="flex flex-col gap-0.5">
                  <span className="font-semibold">{exp.title}</span>
                  <span className="text-sm text-muted-foreground">{exp.company}</span>
                  <span className="text-xs text-muted-foreground">
                    {formatDateRange(exp.startDate, exp.endDate, locale)}
                  </span>
                  {exp.description && (
                    <p className="mt-1 text-sm leading-relaxed">{exp.description}</p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Education */}
      {profile.education.length > 0 && (
        <section aria-label="Education">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Education
          </h3>
          <ul className="flex flex-col gap-4">
            {profile.education.map((edu) => (
              <li key={edu.id} className="border-l-2 border-border pl-4">
                <div className="flex flex-col gap-0.5">
                  <span className="font-semibold">
                    {edu.degree}
                    {edu.field ? ` — ${edu.field}` : ""}
                  </span>
                  <span className="text-sm text-muted-foreground">{edu.institution}</span>
                  <span className="text-xs text-muted-foreground">
                    {formatDateRange(edu.startDate, edu.endDate, locale)}
                  </span>
                  {edu.grade && (
                    <span className="text-xs text-muted-foreground">Grade: {edu.grade}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Skills */}
      {profile.skills.length > 0 && (
        <section aria-label="Skills">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Skills
          </h3>
          <div className="flex flex-col gap-4">
            {SKILL_CATEGORY_ORDER.map((category) => {
              const skills = groupedSkills[category];
              if (!skills.length) return null;
              return (
                <div key={category}>
                  <p className="mb-2 text-xs font-medium text-muted-foreground">{category}</p>
                  <div className="flex flex-wrap gap-2">
                    {skills.map((skill) => (
                      <Badge key={skill.id}>
                        {skill.name}
                      </Badge>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
