"use client";

// JobDetailPanel.tsx — Right-panel slide-over for job detail (FE-5.5)
// Tabs: Overview, Company Research, Contacts, Documents

import { useState } from "react";
import type { SavedJob } from "../types";
import { CompanyResearchCard } from "./CompanyResearchCard";
import { ContactsList } from "./ContactsList";

type Tab = "overview" | "company" | "contacts" | "documents";

const TABS: { id: Tab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "company", label: "Company Research" },
  { id: "contacts", label: "Contacts" },
  { id: "documents", label: "Documents" },
];

interface JobDetailPanelProps {
  job: SavedJob | null;
  onClose: () => void;
}

export function JobDetailPanel({ job, onClose }: JobDetailPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  if (!job) return null;

  return (
    <div
      className="fixed inset-y-0 right-0 z-40 flex w-full max-w-lg flex-col bg-background border-l border-border shadow-xl"
      role="complementary"
      aria-label={`Job detail: ${job.title} at ${job.company}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between border-b border-border p-4">
        <div>
          <h2 className="text-base font-semibold">{job.title}</h2>
          <p className="text-sm text-muted-foreground">{job.company}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close job detail panel"
          className="text-muted-foreground hover:text-foreground"
        >
          ✕
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={[
              "flex-1 px-2 py-3 text-xs font-medium transition-colors",
              activeTab === tab.id
                ? "border-b-2 border-primary text-primary"
                : "text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === "overview" && (
          <div className="flex flex-col gap-3">
            {job.location && (
              <div>
                <span className="text-xs font-semibold text-muted-foreground">Location</span>
                <p className="text-sm">{job.location}</p>
              </div>
            )}
            {job.remote_preference && (
              <div>
                <span className="text-xs font-semibold text-muted-foreground">Remote</span>
                <p className="text-sm">{job.remote_preference}</p>
              </div>
            )}
            {job.description && (
              <div>
                <span className="text-xs font-semibold text-muted-foreground">Description</span>
                <p className="text-sm leading-relaxed whitespace-pre-wrap mt-1">{job.description}</p>
              </div>
            )}
          </div>
        )}

        {activeTab === "company" && <CompanyResearchCard jobId={job.id} />}

        {activeTab === "contacts" && <ContactsList jobId={job.id} />}

        {activeTab === "documents" && (
          <p className="text-sm text-muted-foreground">Documents will be available in a future update.</p>
        )}
      </div>
    </div>
  );
}
