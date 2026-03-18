"use client";

// AddJobDialog.tsx — Add job via URL or manual fields (FE-5.2)

import { useState } from "react";
import { useFocusTrap } from "@repo/ui/hooks";
import { useParseJobUrl, useAddJob } from "../hooks/useAddJob";
import type { AddJobPayload, RemotePreference } from "../types";

interface AddJobDialogProps {
  open: boolean;
  onClose: () => void;
}

type Mode = "url" | "manual";

export function AddJobDialog({ open, onClose }: AddJobDialogProps) {
  const [mode, setMode] = useState<Mode>("url");
  const [url, setUrl] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [salaryMin, setSalaryMin] = useState("");
  const [salaryMax, setSalaryMax] = useState("");
  const [remotePreference, setRemotePreference] = useState<RemotePreference | "">("");

  const parseJobUrl = useParseJobUrl();
  const addJob = useAddJob(onClose);

  const { dialogRef, handleBackdropClick } = useFocusTrap({ open, onClose: handleClose });

  const descriptionTooShort = description.length > 0 && description.length < 100;

  function resetForm() {
    setUrl("");
    setTitle("");
    setCompany("");
    setLocation("");
    setDescription("");
    setSalaryMin("");
    setSalaryMax("");
    setRemotePreference("");
    setParseError(null);
    setMode("url");
  }

  function handleClose() {
    resetForm();
    onClose();
  }

  async function handleParse() {
    if (!url.trim()) return;
    const trimmedUrl = url.trim();
    if (!trimmedUrl.startsWith("http://") && !trimmedUrl.startsWith("https://")) {
      setParseError("URL must start with http:// or https://");
      return;
    }
    setParseError(null);

    parseJobUrl.mutate(
      { url: url.trim() },
      {
        onSuccess: (result) => {
          if (result.title) setTitle(result.title);
          if (result.company) setCompany(result.company);
          if (result.location) setLocation(result.location ?? "");
          if (result.description) setDescription(result.description ?? "");
          setMode("manual");
        },
        onError: () => {
          setParseError("Couldn't parse this URL — please enter details manually");
          setMode("manual");
        },
      }
    );
  }

  function handleSave() {
    if (!title.trim() || !company.trim()) return;

    const payload: AddJobPayload = {
      title: title.trim(),
      company: company.trim(),
      location: location.trim() || undefined,
      description: description.trim() || undefined,
      url: url.trim() || undefined,
      salary_min: salaryMin ? Number(salaryMin) : undefined,
      salary_max: salaryMax ? Number(salaryMax) : undefined,
      remote_preference: remotePreference || undefined,
    };

    addJob.mutate(payload);
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={handleBackdropClick}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-label="Add job"
        aria-modal="true"
        className="relative w-full max-w-md rounded-lg bg-background border border-border p-6 shadow-lg"
      >
        <button
          type="button"
          aria-label="Close dialog"
          onClick={handleClose}
          className="absolute top-3 right-3 text-muted-foreground hover:text-foreground"
        >
          ✕
        </button>

        <h2 className="mb-4 text-base font-semibold">Add job</h2>

        {mode === "url" && (
          <div className="flex flex-col gap-3">
            <label className="text-sm font-medium" htmlFor="job-url">
              Paste job URL
            </label>
            <div className="flex gap-2">
              <input
                id="job-url"
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void handleParse();
                }}
                placeholder="https://..."
                className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
              <button
                type="button"
                onClick={() => void handleParse()}
                disabled={parseJobUrl.isPending || !url.trim()}
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
              >
                {parseJobUrl.isPending ? "Parsing…" : "Parse"}
              </button>
            </div>

            <button
              type="button"
              onClick={() => setMode("manual")}
              className="self-start text-xs text-muted-foreground underline hover:no-underline"
            >
              Enter manually
            </button>
          </div>
        )}

        {mode === "manual" && (
          <div className="flex flex-col gap-3">
            {parseError && (
              <p role="alert" className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800">
                {parseError}
              </p>
            )}

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium" htmlFor="job-title">
                Job title <span aria-hidden="true">*</span>
              </label>
              <input
                id="job-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Software Engineer"
                aria-required="true"
                className="rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium" htmlFor="job-company">
                Company <span aria-hidden="true">*</span>
              </label>
              <input
                id="job-company"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="Acme Corp"
                aria-required="true"
                className="rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium" htmlFor="job-location">
                Location
              </label>
              <input
                id="job-location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Remote / Bengaluru"
                className="rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium" htmlFor="job-remote">
                Job type
              </label>
              <select
                id="job-remote"
                value={remotePreference}
                onChange={(e) => setRemotePreference(e.target.value as RemotePreference | "")}
                className="rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Select…</option>
                <option value="Remote">Remote</option>
                <option value="Hybrid">Hybrid</option>
                <option value="On-site">On-site</option>
              </select>
            </div>

            <div className="flex gap-2">
              <div className="flex flex-col gap-1 flex-1">
                <label className="text-sm font-medium" htmlFor="job-salary-min">
                  Salary min
                </label>
                <input
                  id="job-salary-min"
                  type="number"
                  value={salaryMin}
                  onChange={(e) => setSalaryMin(e.target.value)}
                  placeholder="e.g. 800000"
                  className="rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div className="flex flex-col gap-1 flex-1">
                <label className="text-sm font-medium" htmlFor="job-salary-max">
                  Salary max
                </label>
                <input
                  id="job-salary-max"
                  type="number"
                  value={salaryMax}
                  onChange={(e) => setSalaryMax(e.target.value)}
                  placeholder="e.g. 1200000"
                  className="rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium" htmlFor="job-description">
                Job description
              </label>
              <textarea
                id="job-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Paste the job description here…"
                rows={4}
                className="rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              />
              {descriptionTooShort && (
                <p role="status" className="text-xs text-amber-600">
                  Add more detail for better AI matching
                </p>
              )}
            </div>

            <div className="flex justify-between items-center mt-2">
              <button
                type="button"
                onClick={() => setMode("url")}
                className="text-xs text-muted-foreground underline hover:no-underline"
              >
                ← Back to URL
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={addJob.isPending || !title.trim() || !company.trim()}
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
              >
                {addJob.isPending ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
