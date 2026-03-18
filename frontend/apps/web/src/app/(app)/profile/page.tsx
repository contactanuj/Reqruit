"use client";

// Profile page — FE-4: Profile & Resume Management

import { useState } from "react";
import { useLocale } from "@repo/ui/hooks";
import { useProfileData } from "@/features/profile/hooks/useProfile";
import { ProfileView } from "@/features/profile/components/ProfileView";
import { ProfileEditor } from "@/features/profile/components/ProfileEditor";
import { ResumeUploadZone } from "@/features/profile/components/ResumeUploadZone";
import { ResumeParseStatus } from "@/features/profile/components/ResumeParseStatus";
import { ResumeVersionList } from "@/features/profile/components/ResumeVersionList";
import { SkillAnalysisCard } from "@/features/profile/components/SkillAnalysisCard";
import { SkeletonProfile } from "@/features/profile/components/SkeletonProfile";
import { EmptyState } from "@repo/ui/components";
import { ErrorBoundary } from "@/shared/ErrorBoundary";

type Tab = "profile" | "resumes" | "skills";

export default function ProfilePage() {
  const { data: profile, isPending } = useProfileData();
  const [activeTab, setActiveTab] = useState<Tab>("profile");
  const [isEditing, setIsEditing] = useState(false);
  const [uploadedResumeId, setUploadedResumeId] = useState<string | null>(null);

  const locale = useLocale();

  const handleUploadSuccess = (resumeId: string) => {
    setUploadedResumeId(resumeId);
  };

  const handleParseComplete = () => {
    setUploadedResumeId(null);
  };

  const handleParseRetry = () => {
    setUploadedResumeId(null);
  };

  const tabs: { id: Tab; label: string }[] = [
    { id: "profile", label: "Profile" },
    { id: "resumes", label: "Resumes" },
    { id: "skills", label: "Skill Analysis" },
  ];

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">My Profile</h1>
        {activeTab === "profile" && profile && !isEditing && (
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            Edit profile
          </button>
        )}
      </div>

      {/* Tab navigation */}
      <div
        role="tablist"
        className="mb-6 flex gap-1 border-b border-border"
        aria-label="Profile sections"
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            id={`tab-${tab.id}`}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`tabpanel-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
            className={[
              "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
              activeTab === tab.id
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Profile tab */}
      {activeTab === "profile" && (
        <div id="tabpanel-profile" role="tabpanel" aria-labelledby="tab-profile">
          <ErrorBoundary section="profile">
            {/* Resume upload/parse flow */}
            {uploadedResumeId ? (
              <div className="mb-6">
                <ResumeParseStatus
                  resumeId={uploadedResumeId}
                  onComplete={handleParseComplete}
                  onRetry={handleParseRetry}
                />
              </div>
            ) : null}

            {/* Profile editor */}
            {isEditing && profile ? (
              <ProfileEditor
                profile={profile}
                locale={locale}
                onClose={() => setIsEditing(false)}
              />
            ) : isPending ? (
              <SkeletonProfile />
            ) : profile ? (
              <ProfileView profile={profile} locale={locale} />
            ) : (
              // No profile yet — show empty state + upload zone
              <div className="flex flex-col gap-6">
                <EmptyState
                  aria-label="No profile data"
                  title="No resume uploaded yet"
                  description="Upload your resume to get started. We'll parse it and populate your profile automatically."
                />
                <ResumeUploadZone onUploadSuccess={handleUploadSuccess} />
              </div>
            )}
          </ErrorBoundary>
        </div>
      )}

      {/* Resumes tab */}
      {activeTab === "resumes" && (
        <div id="tabpanel-resumes" role="tabpanel" aria-labelledby="tab-resumes" className="flex flex-col gap-6">
          <ErrorBoundary section="resumes">
            <ResumeVersionList locale={locale} />
            <div className="border-t border-border pt-6">
              <h2 className="mb-3 text-sm font-semibold">Upload a new resume</h2>
              <ResumeUploadZone onUploadSuccess={handleUploadSuccess} />
            </div>
          </ErrorBoundary>
        </div>
      )}

      {/* Skill Analysis tab */}
      {activeTab === "skills" && (
        <div id="tabpanel-skills" role="tabpanel" aria-labelledby="tab-skills">
          <ErrorBoundary section="skill analysis">
            <SkillAnalysisCard />
          </ErrorBoundary>
        </div>
      )}
    </div>
  );
}
