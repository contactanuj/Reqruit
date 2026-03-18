"use client";

// PathPlanner — FE-13.3
// Form to add up to 3 role titles and generate career path projections.

import { useState } from "react";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { useProfileData } from "@/features/profile/hooks/useProfile";
import { useGenerateProjections } from "../hooks/usePathProjections";
import { ProjectionCard } from "./ProjectionCard";

const MAX_ROLES = 3;

export function PathPlanner() {
  const [roles, setRoles] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState("");

  const dailyCredits = useCreditsStore((s) => s.dailyCredits);
  const hasCredits = dailyCredits > 0;
  const { data: profile } = useProfileData();

  const mutation = useGenerateProjections();

  function handleAddRole() {
    const trimmed = inputValue.trim();
    if (!trimmed || roles.length >= MAX_ROLES) return;
    if (roles.includes(trimmed)) return;
    setRoles([...roles, trimmed]);
    setInputValue("");
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddRole();
    }
  }

  function handleRemoveRole(index: number) {
    setRoles(roles.filter((_, i) => i !== index));
  }

  function handleGenerate() {
    if (roles.length === 0) return;
    mutation.mutate({
      roleTitles: roles,
      currentSkills: profile?.skills?.map((s) => s.name) ?? [],
      currentExperience: profile?.experience?.map((e) => ({
        title: e.title,
        company: e.company,
      })) ?? [],
    });
  }

  return (
    <div data-testid="path-planner" className="space-y-4">
      <div className="flex gap-2">
        <input
          data-testid="role-input"
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter a role title"
          className="flex-1 rounded-md border border-border px-3 py-2 text-sm"
          aria-label="Role title input"
        />
        <button
          type="button"
          data-testid="add-role-button"
          onClick={handleAddRole}
          disabled={roles.length >= MAX_ROLES || !inputValue.trim()}
          aria-disabled={roles.length >= MAX_ROLES || !inputValue.trim()}
          className="rounded-md bg-secondary px-3 py-2 text-sm font-medium disabled:opacity-50"
        >
          Add
        </button>
      </div>

      {roles.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {roles.map((role, index) => (
            <span
              key={role}
              className="inline-flex items-center gap-1 rounded-full bg-muted px-3 py-1 text-sm"
            >
              {role}
              <button
                type="button"
                onClick={() => handleRemoveRole(index)}
                aria-label={`Remove ${role}`}
                className="ml-1 text-muted-foreground hover:text-foreground"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      )}

      <button
        type="button"
        data-testid="generate-projections-button"
        onClick={handleGenerate}
        disabled={roles.length === 0 || !hasCredits || mutation.isPending}
        aria-disabled={roles.length === 0 || !hasCredits || mutation.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
      >
        {mutation.isPending ? "Generating\u2026" : "Generate projections"}
      </button>

      {!hasCredits && (
        <p className="text-sm text-destructive">Insufficient credits</p>
      )}

      {mutation.data && (
        <div className="mt-6 space-y-4">
          {mutation.data.map((projection) => (
            <ProjectionCard key={projection.roleTitle} projection={projection} />
          ))}
        </div>
      )}
    </div>
  );
}
