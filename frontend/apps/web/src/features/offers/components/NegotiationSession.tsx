"use client";

// NegotiationSession.tsx — FE-12.4: Three-section streaming negotiation view
// Sections: Strategy, Conversation Script, Email Draft.
// HITL review is shown for the Email Draft section only.

import * as React from "react";
import DOMPurify from "dompurify";
import { HITLReviewPanel } from "@repo/ui/components/HITLReviewPanel";
import { useStreamStore } from "@/features/applications/store/stream-store";
import type { NegotiationSections } from "../types";

interface NegotiationSessionProps {
  sections: NegotiationSections;
  isStreaming: boolean;
  isComplete: boolean;
  offerId: string;
  onApproveEmail: () => void;
  onReviseEmail: (feedback: string) => void;
  isApproving?: boolean;
  isRevising?: boolean;
  onReset: () => void;
}

export function NegotiationSession({
  sections,
  isStreaming,
  isComplete,
  offerId,
  onApproveEmail,
  onReviseEmail,
  isApproving = false,
  isRevising = false,
  onReset,
}: NegotiationSessionProps) {
  const hitlDraft = useStreamStore((s) => s.hitlDraft);
  const hasSections =
    sections.strategy || sections.conversationScript || sections.emailDraft;

  // Show HITL for email draft when streaming is complete and we have an email draft
  const showEmailHITL = isComplete && sections.emailDraft;

  return (
    <div data-testid="negotiation-session" className="space-y-6">
      {/* Streaming indicator */}
      {isStreaming && (
        <div
          data-testid="negotiation-streaming"
          aria-live="polite"
          className="flex items-center gap-2 text-sm text-muted-foreground"
        >
          <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
          Generating negotiation strategy...
        </div>
      )}

      {/* Strategy section */}
      {sections.strategy && (
        <section data-testid="section-strategy" className="space-y-2">
          <h3 className="text-sm font-semibold text-foreground">Strategy</h3>
          <div
            className={`whitespace-pre-wrap rounded-md border p-4 text-sm text-foreground ${
              isComplete
                ? "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20"
                : "border-border"
            }`}
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(sections.strategy),
            }}
          />
        </section>
      )}

      {/* Conversation Script section */}
      {sections.conversationScript && (
        <section data-testid="section-conversation-script" className="space-y-2">
          <h3 className="text-sm font-semibold text-foreground">
            Conversation Script
          </h3>
          <div
            className={`whitespace-pre-wrap rounded-md border p-4 text-sm text-foreground ${
              isComplete
                ? "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20"
                : "border-border"
            }`}
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(sections.conversationScript),
            }}
          />
        </section>
      )}

      {/* Email Draft section — with HITL review */}
      {sections.emailDraft && !showEmailHITL && (
        <section data-testid="section-email-draft" className="space-y-2">
          <h3 className="text-sm font-semibold text-foreground">
            Email Draft
          </h3>
          <div
            className="whitespace-pre-wrap rounded-md border border-border p-4 text-sm text-foreground"
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(sections.emailDraft),
            }}
          />
        </section>
      )}

      {/* HITL Review for Email Draft — only shown when complete */}
      {showEmailHITL && (
        <section data-testid="email-hitl-review" className="space-y-2">
          <h3 className="text-sm font-semibold text-foreground">
            Email Draft — Review & Approve
          </h3>
          <div className="h-[350px]">
            <HITLReviewPanel
              draftContent={DOMPurify.sanitize(
                hitlDraft?.content ?? sections.emailDraft,
              )}
              sourceContent={DOMPurify.sanitize(
                `Offer ID: ${offerId}\n\nStrategy: ${sections.strategy}`,
              )}
              sourceTitle="Negotiation Context"
              onApprove={onApproveEmail}
              onRevise={onReviseEmail}
              isApproving={isApproving}
              isRevising={isRevising}
            />
          </div>
        </section>
      )}

      {/* Reset button */}
      {isComplete && hasSections && (
        <button
          type="button"
          data-testid="reset-negotiation-button"
          onClick={onReset}
          className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          Start new negotiation
        </button>
      )}
    </div>
  );
}
