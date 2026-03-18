// SourcePane.tsx — Read-only job description pane (FE-7.3)

import * as React from "react";

interface SourcePaneProps {
  content: string;
  title?: string;
}

export function SourcePane({ content, title = "Job Description" }: SourcePaneProps) {
  return (
    <div
      className="flex h-full flex-col overflow-hidden"
      aria-label="Job description"
    >
      <div className="flex-shrink-0 border-b border-border px-4 py-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {title}
        </span>
      </div>
      <div
        className="flex-1 overflow-y-auto whitespace-pre-wrap p-4 text-sm leading-relaxed"
        data-testid="source-pane"
        aria-readonly="true"
      >
        {content}
      </div>
    </div>
  );
}
