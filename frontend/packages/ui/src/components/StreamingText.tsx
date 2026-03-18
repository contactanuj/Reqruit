// StreamingText.tsx — Renders AI-streamed tokens with a blinking cursor.
// UX-6: respects prefers-reduced-motion — animation disabled when set.
// UX-7: aria-live="polite" aria-atomic="false" — screen readers announce
//        each new token without interrupting ongoing speech.

import * as React from "react";

import styles from "./StreamingText.module.css";

export interface StreamingTextProps {
  /** The accumulated text to display. */
  text: string;
  /** Shows the blinking cursor when true (i.e., stream is active). */
  isStreaming?: boolean;
  /** Additional class names applied to the wrapping <span>. */
  className?: string;
}

export function StreamingText({
  text,
  isStreaming = false,
  className,
}: StreamingTextProps) {
  return (
    <span
      aria-live="polite"
      aria-atomic="false"
      className={className}
    >
      {text}
      {isStreaming && (
        <span
          className={styles.cursor}
          aria-hidden="true"
          data-testid="streaming-cursor"
        />
      )}
    </span>
  );
}
