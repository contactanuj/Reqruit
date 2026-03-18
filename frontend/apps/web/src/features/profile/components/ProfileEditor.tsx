"use client";

// ProfileEditor.tsx — FE-4.4: Profile edit form

import { useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { ApiError } from "@reqruit/api-client";
import { useUpdateProfile } from "../hooks/useProfile";
import { formatLPA } from "@repo/ui/lib/locale";
import type { LocaleCode } from "@repo/ui/lib/locale";
import type { Profile, UpdateProfilePayload } from "../types";

const salaryRangeSchema = z.object({
  min: z.number().positive("Salary min must be a positive number"),
  max: z.number().positive("Salary max must be a positive number"),
}).refine((data) => data.min < data.max, {
  message: "Minimum salary must be less than maximum salary",
  path: ["max"],
});

interface ProfileEditorProps {
  profile: Profile;
  onClose?: () => void;
  locale: LocaleCode;
}

const REMOTE_OPTIONS = ["Remote", "Hybrid", "On-site"] as const;
const NOTICE_PERIOD_OPTIONS_IN = [0, 15, 30, 45, 60, 90];
const NOTICE_PERIOD_OPTIONS_US = [0, 14, 30, 60, 90];

export function ProfileEditor({ profile, onClose, locale }: ProfileEditorProps) {
  const { mutate: updateProfile, isPending } = useUpdateProfile();
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  // Form state
  const [headline, setHeadline] = useState(profile.headline ?? "");
  const [summary, setSummary] = useState(profile.summary ?? "");
  const [remotePreference, setRemotePreference] = useState<
    "Remote" | "Hybrid" | "On-site" | undefined
  >(profile.remotePreference);
  const [location, setLocation] = useState(profile.contact.location ?? "");
  const [noticePeriod, setNoticePeriod] = useState<number | undefined>(profile.noticePeriod);
  const [targetRolesInput, setTargetRolesInput] = useState("");
  const [targetRoles, setTargetRoles] = useState<string[]>(profile.targetRoles);
  const [targetCompanies, setTargetCompanies] = useState(
    profile.targetCompanies?.join(", ") ?? ""
  );
  const [visaRequirement, setVisaRequirement] = useState(
    profile.visaRequirement ?? ""
  );
  const [salaryMin, setSalaryMin] = useState<string>(
    profile.salaryRange ? String(profile.salaryRange.min) : ""
  );
  const [salaryMax, setSalaryMax] = useState<string>(
    profile.salaryRange ? String(profile.salaryRange.max) : ""
  );

  const handleAddRole = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const role = targetRolesInput.trim();
      if (role && !targetRoles.includes(role)) {
        setTargetRoles([...targetRoles, role]);
      }
      setTargetRolesInput("");
    }
  };

  const handleRemoveRole = (role: string) => {
    setTargetRoles(targetRoles.filter((r) => r !== role));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const payload: UpdateProfilePayload = {
      headline: headline || undefined,
      summary: summary || undefined,
      targetRoles,
      targetCompanies: targetCompanies
        ? targetCompanies.split(",").map((s) => s.trim()).filter(Boolean)
        : undefined,
      remotePreference,
      location: location || undefined,
      noticePeriod,
      visaRequirement: visaRequirement || undefined,
    };

    if (salaryMin || salaryMax) {
      const salaryResult = salaryRangeSchema.safeParse({
        min: Number(salaryMin) || 0,
        max: Number(salaryMax) || 0,
      });
      if (!salaryResult.success) {
        const mapped: Record<string, string> = {};
        for (const issue of salaryResult.error.issues) {
          const field = issue.path[0] === "min" ? "salaryMin" : "salaryMax";
          mapped[field] = issue.message;
        }
        setFieldErrors(mapped);
        return;
      }
      payload.salaryRange = salaryResult.data;
    }

    setFieldErrors({});
    updateProfile(payload, {
      onSuccess: () => {
        onClose?.();
      },
      onError: (err) => {
        if (err instanceof ApiError && err.status === 422) {
          const errors = (err.body as { detail?: Array<{ loc?: string[]; msg: string }> })?.detail ?? [];
          const mapped: Record<string, string> = {};
          for (const e of errors) {
            const field = e.loc?.[e.loc.length - 1];
            if (field) mapped[field] = e.msg;
          }
          setFieldErrors(mapped);
          const firstField = Object.keys(mapped)[0];
          if (firstField) {
            (document.querySelector(`[name="${firstField}"]`) as HTMLElement | null)?.focus();
          }
        } else {
          toast.error("Failed to save profile");
        }
      },
    });
  };

  const noticePeriodOptions =
    locale === "IN" ? NOTICE_PERIOD_OPTIONS_IN : NOTICE_PERIOD_OPTIONS_US;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5">
      <h2 className="text-lg font-semibold">Edit Profile</h2>

      {/* Headline */}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="headline" className="text-sm font-medium">
          Headline
        </label>
        <input
          id="headline"
          name="headline"
          type="text"
          value={headline}
          onChange={(e) => setHeadline(e.target.value)}
          placeholder="e.g. Senior Software Engineer"
          disabled={isPending}
          aria-describedby={fieldErrors.headline ? "headline-error" : undefined}
          aria-invalid={!!fieldErrors.headline}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        />
        {fieldErrors.headline && (
          <p id="headline-error" role="alert" className="text-xs text-destructive">{fieldErrors.headline}</p>
        )}
      </div>

      {/* Summary */}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="summary" className="text-sm font-medium">
          Summary
        </label>
        <textarea
          id="summary"
          name="summary"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={4}
          placeholder="Tell us about yourself…"
          disabled={isPending}
          aria-describedby={fieldErrors.summary ? "summary-error" : undefined}
          aria-invalid={!!fieldErrors.summary}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 resize-y"
        />
        {fieldErrors.summary && (
          <p id="summary-error" role="alert" className="text-xs text-destructive">{fieldErrors.summary}</p>
        )}
      </div>

      {/* Target Roles */}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="targetRoles" className="text-sm font-medium">
          Target Roles
        </label>
        <div className="flex flex-wrap gap-1.5 rounded-md border border-input bg-background p-2">
          {targetRoles.map((role) => (
            <span
              key={role}
              className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary"
            >
              {role}
              <button
                type="button"
                onClick={() => handleRemoveRole(role)}
                aria-label={`Remove ${role}`}
                className="text-primary/70 hover:text-primary"
              >
                ×
              </button>
            </span>
          ))}
          <input
            id="targetRoles"
            type="text"
            value={targetRolesInput}
            onChange={(e) => setTargetRolesInput(e.target.value)}
            onKeyDown={handleAddRole}
            placeholder="Add role and press Enter…"
            disabled={isPending}
            className="flex-1 min-w-24 bg-transparent text-sm outline-none disabled:opacity-50"
          />
        </div>
        <p className="text-xs text-muted-foreground">Press Enter to add a role</p>
      </div>

      {/* Remote Preference */}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="remotePreference" className="text-sm font-medium">
          Remote Preference
        </label>
        <select
          id="remotePreference"
          name="remotePreference"
          value={remotePreference ?? ""}
          onChange={(e) =>
            setRemotePreference(
              (e.target.value as "Remote" | "Hybrid" | "On-site") || undefined
            )
          }
          disabled={isPending}
          aria-describedby={fieldErrors.remotePreference ? "remotePreference-error" : undefined}
          aria-invalid={!!fieldErrors.remotePreference}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        >
          <option value="">Select…</option>
          {REMOTE_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
        {fieldErrors.remotePreference && (
          <p id="remotePreference-error" role="alert" className="text-xs text-destructive">{fieldErrors.remotePreference}</p>
        )}
      </div>

      {/* Location */}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="location" className="text-sm font-medium">
          Location
        </label>
        <input
          id="location"
          name="location"
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="e.g. Bengaluru, India"
          disabled={isPending}
          aria-describedby={fieldErrors.location ? "location-error" : undefined}
          aria-invalid={!!fieldErrors.location}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        />
        {fieldErrors.location && (
          <p id="location-error" role="alert" className="text-xs text-destructive">{fieldErrors.location}</p>
        )}
      </div>

      {/* Target Companies */}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="targetCompanies" className="text-sm font-medium">
          Target Companies
        </label>
        <input
          id="targetCompanies"
          name="targetCompanies"
          type="text"
          value={targetCompanies}
          onChange={(e) => setTargetCompanies(e.target.value)}
          placeholder="e.g. Google, Microsoft, Stripe"
          disabled={isPending}
          aria-describedby={fieldErrors.targetCompanies ? "targetCompanies-error" : undefined}
          aria-invalid={!!fieldErrors.targetCompanies}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        />
        <p className="text-xs text-muted-foreground">Comma-separated list of companies</p>
        {fieldErrors.targetCompanies && (
          <p id="targetCompanies-error" role="alert" className="text-xs text-destructive">{fieldErrors.targetCompanies}</p>
        )}
      </div>

      {/* Visa Requirement */}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="visaRequirement" className="text-sm font-medium">
          Visa Requirement
        </label>
        <select
          id="visaRequirement"
          name="visaRequirement"
          value={visaRequirement}
          onChange={(e) => setVisaRequirement(e.target.value)}
          disabled={isPending}
          aria-describedby={fieldErrors.visaRequirement ? "visaRequirement-error" : undefined}
          aria-invalid={!!fieldErrors.visaRequirement}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        >
          <option value="">Select…</option>
          <option value="No visa required">No visa required</option>
          <option value="Need sponsorship">Need sponsorship</option>
          <option value="Have work authorization">Have work authorization</option>
        </select>
        {fieldErrors.visaRequirement && (
          <p id="visaRequirement-error" role="alert" className="text-xs text-destructive">{fieldErrors.visaRequirement}</p>
        )}
      </div>

      {/* Salary Range — locale-aware */}
      <div className="flex flex-col gap-1.5">
        <p className="text-sm font-medium">
          Salary Range{" "}
          <span className="text-xs text-muted-foreground">
            ({locale === "IN" ? "LPA — e.g. 1800000 for ₹18L" : "USD — e.g. 180000 for $180K"})
          </span>
        </p>
        <div className="flex gap-2">
          <input
            type="number"
            aria-label="Salary minimum"
            value={salaryMin}
            onChange={(e) => setSalaryMin(e.target.value)}
            placeholder="Min"
            disabled={isPending}
            aria-describedby={fieldErrors.salaryMin ? "salaryMin-error" : undefined}
            aria-invalid={!!fieldErrors.salaryMin}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
          />
          <span className="flex items-center text-muted-foreground">–</span>
          <input
            type="number"
            aria-label="Salary maximum"
            value={salaryMax}
            onChange={(e) => setSalaryMax(e.target.value)}
            placeholder="Max"
            disabled={isPending}
            aria-describedby={fieldErrors.salaryMax ? "salaryMax-error" : undefined}
            aria-invalid={!!fieldErrors.salaryMax}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
          />
        </div>
        {salaryMin && !fieldErrors.salaryMin && (
          <p className="text-xs text-muted-foreground">
            {formatLPA(Number(salaryMin), locale)}
            {salaryMax && !fieldErrors.salaryMax ? ` – ${formatLPA(Number(salaryMax), locale)}` : ""}
          </p>
        )}
        {fieldErrors.salaryMin && (
          <p id="salaryMin-error" role="alert" className="text-xs text-destructive">{fieldErrors.salaryMin}</p>
        )}
        {fieldErrors.salaryMax && (
          <p id="salaryMax-error" role="alert" className="text-xs text-destructive">{fieldErrors.salaryMax}</p>
        )}
      </div>

      {/* Notice Period */}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="noticePeriod" className="text-sm font-medium">
          Notice Period (days)
        </label>
        <select
          id="noticePeriod"
          name="noticePeriod"
          value={noticePeriod ?? ""}
          onChange={(e) =>
            setNoticePeriod(e.target.value !== "" ? Number(e.target.value) : undefined)
          }
          disabled={isPending}
          aria-describedby={fieldErrors.noticePeriod ? "noticePeriod-error" : undefined}
          aria-invalid={!!fieldErrors.noticePeriod}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
        >
          <option value="">Select…</option>
          {noticePeriodOptions.map((days) => (
            <option key={days} value={days}>
              {days === 0 ? "Immediate" : `${days} days`}
            </option>
          ))}
        </select>
        {fieldErrors.noticePeriod && (
          <p id="noticePeriod-error" role="alert" className="text-xs text-destructive">{fieldErrors.noticePeriod}</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <button
          type="submit"
          disabled={isPending}
          className="flex-1 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isPending ? "Saving…" : "Save"}
        </button>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            disabled={isPending}
            className="flex-1 rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
