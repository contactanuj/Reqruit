"use client";

// OutreachDialog.tsx — FE-10.1: AI Outreach Message Generation & HITL
// Custom dialog (same pattern as AddJobDialog) for choosing outreach type
// (LinkedIn/Email) and tone (Professional/Casual), then generating, reviewing,
// and approving an AI-drafted outreach message.

import * as React from "react";
import DOMPurify from "dompurify";
import { toast } from "sonner";
import { useFocusTrap } from "@repo/ui/hooks";
import { useSSEStream } from "@repo/ui/hooks/use-sse-stream";
import { HITLReviewPanel } from "@repo/ui/components/HITLReviewPanel";
import { StreamingText } from "@repo/ui/components/StreamingText";
import { useStreamStore } from "@/features/applications/store/stream-store";
import { useCreditsStore } from "@/features/credits/store/credits-store";
import { AgentPipelineVisualizer } from "./AgentPipelineVisualizer";
import {
  useOutreachGeneration,
  useApproveOutreach,
} from "../hooks/useOutreachGeneration";
import type { Contact } from "@/features/jobs/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type OutreachType = "linkedin" | "email";
export type OutreachTone = "professional" | "casual";

type DialogPhase = "config" | "generating" | "review" | "approved";

interface OutreachDialogProps {
  jobId: string;
  contact: Contact;
  open: boolean;
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function OutreachDialog({
  jobId,
  contact,
  open,
  onClose,
}: OutreachDialogProps) {
  const [outreachType, setOutreachType] = React.useState<OutreachType>("linkedin");
  const [tone, setTone] = React.useState<OutreachTone>("professional");
  const [phase, setPhase] = React.useState<DialogPhase>("config");
  const [approvedText, setApprovedText] = React.useState("");
  const [copySuccess, setCopySuccess] = React.useState(false);

  // Stores
  const activeThreadId = useStreamStore((s) => s.activeThreadId);
  const streamingBuffer = useStreamStore((s) => s.streamingBuffer);
  const isComplete = useStreamStore((s) => s.isComplete);
  const hitlDraft = useStreamStore((s) => s.hitlDraft);
  const resetStream = useStreamStore((s) => s.reset);
  const dailyCredits = useCreditsStore((s) => s.dailyCredits);

  // Mutations
  const { mutate: generate, isPending: isGenerating } = useOutreachGeneration(
    jobId,
    contact.id,
  );
  const { mutate: approve, isPending: isApproving } = useApproveOutreach(
    jobId,
    contact.id,
  );

  // Focus trap (same pattern as AddJobDialog)
  const { dialogRef, handleBackdropClick } = useFocusTrap({ open, onClose: handleClose });

  // SSE stream — connect when we have a thread ID
  useSSEStream(
    activeThreadId
      ? `/jobs/${jobId}/contacts/${contact.id}/outreach/stream?thread_id=${activeThreadId}`
      : null,
  );

  // Transition to review phase when HITL draft is ready
  React.useEffect(() => {
    if (hitlDraft && phase === "generating") {
      setPhase("review");
    }
  }, [hitlDraft, phase]);

  // Transition to generating phase when thread starts
  React.useEffect(() => {
    if (activeThreadId && phase === "config") {
      setPhase("generating");
    }
  }, [activeThreadId, phase]);

  function handleClose() {
    setPhase("config");
    setOutreachType("linkedin");
    setTone("professional");
    setApprovedText("");
    setCopySuccess(false);
    resetStream();
    onClose();
  }

  // Contact context for the source pane (sanitized)
  const contactContext = React.useMemo(() => {
    const raw = [
      `Name: ${contact.name}`,
      contact.role_type ? `Role: ${contact.role_type}` : null,
      contact.email ? `Email: ${contact.email}` : null,
      contact.linkedin_url ? `LinkedIn: ${contact.linkedin_url}` : null,
    ]
      .filter(Boolean)
      .join("\n");
    return DOMPurify.sanitize(raw);
  }, [contact]);

  const handleGenerate = () => {
    generate({ type: outreachType, tone });
  };

  const handleApprove = () => {
    const finalText = hitlDraft?.content ?? streamingBuffer;
    approve(
      { text: finalText },
      {
        onSuccess: () => {
          setApprovedText(finalText);
          setPhase("approved");
          toast.success("Outreach message approved");
        },
      },
    );
  };

  const handleRevise = (feedback: string) => {
    resetStream();
    setPhase("generating");
    generate({ type: outreachType, tone, feedback });
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(approvedText);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  };

  const hasCredits = dailyCredits > 0;

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={handleBackdropClick}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-label="Generate outreach message"
        aria-modal="true"
        className="relative mx-4 flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-lg border border-border bg-background shadow-lg md:w-[720px]"
        data-testid="outreach-dialog"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 id="outreach-dialog-title" className="text-lg font-semibold">
            Generate Outreach Message
          </h2>
          <button
            type="button"
            aria-label="Close dialog"
            onClick={handleClose}
            className="rounded-md p-1 text-muted-foreground hover:text-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            data-testid="close-dialog-button"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* ── Config Phase ── */}
          {phase === "config" && (
            <div
              className="space-y-6"
              data-testid="config-phase"
              onKeyDown={(e) => {
                if (e.key === "Enter" && hasCredits && !isGenerating) {
                  e.preventDefault();
                  handleGenerate();
                }
              }}
            >
              {/* Contact confirmation */}
              <div className="rounded-md border border-border bg-muted/50 p-4">
                <p className="text-sm text-muted-foreground">Generating outreach for:</p>
                <p className="mt-1 font-medium" data-testid="contact-name">
                  {DOMPurify.sanitize(contact.name)}
                  {contact.role_type && (
                    <span className="ml-2 text-sm text-muted-foreground">
                      ({DOMPurify.sanitize(contact.role_type)})
                    </span>
                  )}
                </p>
              </div>

              {/* Outreach type selector */}
              <fieldset>
                <legend className="mb-2 text-sm font-medium">Message Type</legend>
                <div
                  className="flex gap-3"
                  role="radiogroup"
                  aria-label="Outreach message type"
                  data-testid="type-selector"
                >
                  <label className="flex cursor-pointer items-center gap-2 rounded-md border border-border px-4 py-2 has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                    <input
                      type="radio"
                      name="outreach-type"
                      value="linkedin"
                      checked={outreachType === "linkedin"}
                      onChange={() => setOutreachType("linkedin")}
                      className="accent-primary"
                    />
                    <span className="text-sm">LinkedIn message</span>
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 rounded-md border border-border px-4 py-2 has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                    <input
                      type="radio"
                      name="outreach-type"
                      value="email"
                      checked={outreachType === "email"}
                      onChange={() => setOutreachType("email")}
                      className="accent-primary"
                    />
                    <span className="text-sm">Email message</span>
                  </label>
                </div>
              </fieldset>

              {/* Tone selector */}
              <fieldset>
                <legend className="mb-2 text-sm font-medium">Tone</legend>
                <div
                  className="flex gap-3"
                  role="radiogroup"
                  aria-label="Outreach tone"
                  data-testid="tone-selector"
                >
                  <label className="flex cursor-pointer items-center gap-2 rounded-md border border-border px-4 py-2 has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                    <input
                      type="radio"
                      name="outreach-tone"
                      value="professional"
                      checked={tone === "professional"}
                      onChange={() => setTone("professional")}
                      className="accent-primary"
                    />
                    <span className="text-sm">Professional</span>
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 rounded-md border border-border px-4 py-2 has-[:checked]:border-primary has-[:checked]:bg-primary/5">
                    <input
                      type="radio"
                      name="outreach-tone"
                      value="casual"
                      checked={tone === "casual"}
                      onChange={() => setTone("casual")}
                      className="accent-primary"
                    />
                    <span className="text-sm">Casual</span>
                  </label>
                </div>
              </fieldset>
            </div>
          )}

          {/* ── Generating Phase ── */}
          {phase === "generating" && activeThreadId && (
            <div data-testid="generating-phase">
              <AgentPipelineVisualizer
                threadId={activeThreadId}
                streamUrl={`/jobs/${jobId}/contacts/${contact.id}/outreach/stream`}
                onComplete={() => {}}
                onError={() => toast.error("Generation failed — please try again")}
              />
              <div className="mt-4">
                <StreamingText text={streamingBuffer} isStreaming={!isComplete} />
              </div>
            </div>
          )}

          {/* ── Review Phase (HITL) ── */}
          {phase === "review" && (
            <div className="h-[400px]" data-testid="review-phase">
              <HITLReviewPanel
                draftContent={DOMPurify.sanitize(
                  hitlDraft?.content ?? streamingBuffer,
                )}
                sourceContent={contactContext}
                sourceTitle="Contact Context"
                onApprove={handleApprove}
                onRevise={handleRevise}
                isApproving={isApproving}
              />
            </div>
          )}

          {/* ── Approved Phase ── */}
          {phase === "approved" && (
            <div className="space-y-4" data-testid="approved-phase">
              <div className="rounded-md border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-900/20">
                <p className="mb-2 text-sm font-medium text-green-800 dark:text-green-300">
                  Message approved and saved
                </p>
                <div className="whitespace-pre-wrap text-sm">
                  {DOMPurify.sanitize(approvedText)}
                </div>
              </div>
              <button
                type="button"
                onClick={handleCopy}
                className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                data-testid="copy-to-clipboard-button"
                aria-live="polite"
              >
                {copySuccess ? "Copied!" : "Copy to clipboard"}
              </button>
            </div>
          )}
        </div>

        {/* Footer — only in config phase */}
        {phase === "config" && (
          <div className="flex items-center justify-end gap-2 border-t border-border px-6 py-4">
            <button
              type="button"
              onClick={handleClose}
              className="rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              data-testid="cancel-button"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={isGenerating || !hasCredits}
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50"
              data-testid="generate-button"
            >
              {isGenerating ? "Starting…" : "Generate"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
