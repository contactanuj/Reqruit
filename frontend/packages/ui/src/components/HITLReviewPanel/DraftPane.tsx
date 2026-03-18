// DraftPane.tsx — Editable AI-generated cover letter pane (FE-7.3)

import * as React from "react";

interface DraftPaneProps {
  content: string;
  isEditable?: boolean;
  onChange?: (content: string) => void;
}

export function DraftPane({ content, isEditable = false, onChange }: DraftPaneProps) {
  const [localContent, setLocalContent] = React.useState(content);

  // Sync external content changes (e.g., new HITL draft from revision)
  React.useEffect(() => {
    setLocalContent(content);
  }, [content]);

  const handleInput = (e: React.FormEvent<HTMLDivElement>) => {
    const text = e.currentTarget.innerText ?? "";
    setLocalContent(text);
    onChange?.(text);
  };

  return (
    <div
      className="flex h-full flex-col overflow-hidden"
      aria-label="AI-generated cover letter"
    >
      <div className="flex-shrink-0 border-b border-border px-4 py-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          AI Draft
        </span>
      </div>
      {isEditable ? (
        <div
          role="textbox"
          aria-multiline="true"
          aria-label="Edit cover letter"
          contentEditable
          suppressContentEditableWarning
          onInput={handleInput}
          className="flex-1 overflow-y-auto p-4 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-inset focus:ring-primary"
          data-testid="draft-pane-editable"
        >
          {localContent}
        </div>
      ) : (
        <div
          className="flex-1 overflow-y-auto whitespace-pre-wrap p-4 text-sm leading-relaxed"
          data-testid="draft-pane-readonly"
        >
          {localContent}
        </div>
      )}
    </div>
  );
}
