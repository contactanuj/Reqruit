"use client";

// ResumeUploadZone.tsx — FE-4.1: Resume upload via drag-and-drop or file picker

import { useRef, useState } from "react";
import { useResumeUpload } from "../hooks/useResumeUpload";

const ACCEPTED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const ACCEPTED_EXTENSIONS = [".pdf", ".docx"];
const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

interface ResumeUploadZoneProps {
  onUploadSuccess?: (resumeId: string) => void;
}

function validateFile(file: File): string | null {
  const extension = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
  const validExt = ACCEPTED_EXTENSIONS.includes(extension);
  const validMime = ACCEPTED_TYPES.includes(file.type);
  // Accept if extension OR MIME matches. This handles cases where the browser
  // reports empty or application/octet-stream MIME (e.g. .docx on some OSes).
  if (!validExt && !validMime) {
    return "Only PDF and DOCX files are supported";
  }
  if (file.size > MAX_SIZE_BYTES) {
    return "File must be 10MB or smaller";
  }
  return null;
}

export function ResumeUploadZone({ onUploadSuccess }: ResumeUploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { mutate: upload, isPending } = useResumeUpload();

  const handleFile = (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    upload(file, {
      onSuccess: (data) => {
        onUploadSuccess?.(data.id);
      },
    });
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // Reset input so same file can be re-selected
    e.target.value = "";
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      inputRef.current?.click();
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div
        role="button"
        aria-label="Upload resume — drag a file here or click to browse"
        aria-disabled={isPending}
        tabIndex={0}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !isPending && inputRef.current?.click()}
        onKeyDown={handleKeyDown}
        className={[
          "relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 cursor-pointer transition-colors",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
          dragOver
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50 hover:bg-muted/30",
          isPending ? "opacity-60 cursor-not-allowed" : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        {/* Hidden file input */}
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          className="sr-only"
          onChange={handleInputChange}
          disabled={isPending}
          aria-hidden="true"
          tabIndex={-1}
        />

        {isPending ? (
          <div className="flex flex-col items-center gap-2">
            <div className="h-8 w-8 rounded-full border-4 border-primary/30 border-t-primary animate-spin" />
            <p className="text-sm text-muted-foreground">Uploading…</p>
          </div>
        ) : (
          <>
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" x2="12" y1="3" y2="15" />
              </svg>
            </div>
            <div className="text-center">
              <p className="text-sm font-medium">
                Drag &amp; drop your resume here, or{" "}
                <span className="text-primary underline underline-offset-2">browse</span>
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                PDF or DOCX · Max 10MB
              </p>
            </div>
          </>
        )}
      </div>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
