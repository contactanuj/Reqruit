"use client";

// StarStoryForm.tsx — FE-11.1 STAR story create/edit form

import * as React from "react";
import type { StarStory, StarStoryFormData } from "../types";

interface StarStoryFormProps {
  story?: StarStory;
  onSubmit: (data: StarStoryFormData) => void;
  onCancel: () => void;
  isPending?: boolean;
}

interface FieldErrors {
  title?: string;
  situation?: string;
  task?: string;
  action?: string;
  result?: string;
}

const REQUIRED_FIELDS = ["title", "situation", "task", "action", "result"] as const;

export function StarStoryForm({
  story,
  onSubmit,
  onCancel,
  isPending = false,
}: StarStoryFormProps) {
  const [title, setTitle] = React.useState(story?.title ?? "");
  const [situation, setSituation] = React.useState(story?.situation ?? "");
  const [task, setTask] = React.useState(story?.task ?? "");
  const [action, setAction] = React.useState(story?.action ?? "");
  const [result, setResult] = React.useState(story?.result ?? "");
  const [tags, setTags] = React.useState<string[]>(story?.tags ?? []);
  const [tagInputValue, setTagInputValue] = React.useState("");
  const [errors, setErrors] = React.useState<FieldErrors>({});
  const [submitted, setSubmitted] = React.useState(false);

  const values = { title, situation, task, action, result };

  function validate(): FieldErrors {
    const next: FieldErrors = {};
    for (const field of REQUIRED_FIELDS) {
      if (!values[field].trim()) {
        next[field] = `${field.charAt(0).toUpperCase() + field.slice(1)} is required`;
      }
    }
    return next;
  }

  const hasRequiredEmpty = REQUIRED_FIELDS.some((f) => !values[f].trim());

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(true);

    const fieldErrors = validate();
    setErrors(fieldErrors);
    if (Object.keys(fieldErrors).length > 0) return;

    onSubmit({
      title: title.trim(),
      situation: situation.trim(),
      task: task.trim(),
      action: action.trim(),
      result: result.trim(),
      tags,
    });
  }

  // Re-validate on change after first submit attempt
  React.useEffect(() => {
    if (submitted) {
      setErrors(validate());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title, situation, task, action, result, submitted]);

  return (
    <form
      onSubmit={handleSubmit}
      data-testid="star-story-form"
      className="space-y-4"
      noValidate
    >
      {/* Title */}
      <div>
        <label
          htmlFor="star-title"
          className="mb-1 block text-sm font-medium text-foreground"
        >
          Title
        </label>
        <input
          id="star-title"
          data-testid="field-title"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          aria-describedby={errors.title ? "err-title" : undefined}
          aria-invalid={!!errors.title}
          className="min-h-[44px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {errors.title && (
          <p
            id="err-title"
            data-testid="validation-error"
            className="mt-1 text-xs text-red-600"
            role="alert"
          >
            {errors.title}
          </p>
        )}
      </div>

      {/* Situation */}
      <div>
        <label
          htmlFor="star-situation"
          className="mb-1 block text-sm font-medium text-foreground"
        >
          Situation
        </label>
        <textarea
          id="star-situation"
          data-testid="field-situation"
          value={situation}
          onChange={(e) => setSituation(e.target.value)}
          rows={3}
          aria-describedby={errors.situation ? "err-situation" : undefined}
          aria-invalid={!!errors.situation}
          className="min-h-[44px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {errors.situation && (
          <p
            id="err-situation"
            data-testid="validation-error"
            className="mt-1 text-xs text-red-600"
            role="alert"
          >
            {errors.situation}
          </p>
        )}
      </div>

      {/* Task */}
      <div>
        <label
          htmlFor="star-task"
          className="mb-1 block text-sm font-medium text-foreground"
        >
          Task
        </label>
        <textarea
          id="star-task"
          data-testid="field-task"
          value={task}
          onChange={(e) => setTask(e.target.value)}
          rows={3}
          aria-describedby={errors.task ? "err-task" : undefined}
          aria-invalid={!!errors.task}
          className="min-h-[44px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {errors.task && (
          <p
            id="err-task"
            data-testid="validation-error"
            className="mt-1 text-xs text-red-600"
            role="alert"
          >
            {errors.task}
          </p>
        )}
      </div>

      {/* Action */}
      <div>
        <label
          htmlFor="star-action"
          className="mb-1 block text-sm font-medium text-foreground"
        >
          Action
        </label>
        <textarea
          id="star-action"
          data-testid="field-action"
          value={action}
          onChange={(e) => setAction(e.target.value)}
          rows={3}
          aria-describedby={errors.action ? "err-action" : undefined}
          aria-invalid={!!errors.action}
          className="min-h-[44px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {errors.action && (
          <p
            id="err-action"
            data-testid="validation-error"
            className="mt-1 text-xs text-red-600"
            role="alert"
          >
            {errors.action}
          </p>
        )}
      </div>

      {/* Result */}
      <div>
        <label
          htmlFor="star-result"
          className="mb-1 block text-sm font-medium text-foreground"
        >
          Result
        </label>
        <textarea
          id="star-result"
          data-testid="field-result"
          value={result}
          onChange={(e) => setResult(e.target.value)}
          rows={3}
          aria-describedby={errors.result ? "err-result" : undefined}
          aria-invalid={!!errors.result}
          className="min-h-[44px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {errors.result && (
          <p
            id="err-result"
            data-testid="validation-error"
            className="mt-1 text-xs text-red-600"
            role="alert"
          >
            {errors.result}
          </p>
        )}
      </div>

      {/* Tags */}
      <div>
        <label
          htmlFor="star-tags"
          className="mb-1 block text-sm font-medium text-foreground"
        >
          Tags
        </label>
        {tags.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1" data-testid="tag-chips">
            {tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary"
              >
                {tag}
                <button
                  type="button"
                  onClick={() => setTags(tags.filter((t) => t !== tag))}
                  aria-label={`Remove tag ${tag}`}
                  className="ml-0.5 rounded-full p-0.5 hover:bg-primary/20 focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  &times;
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <input
            id="star-tags"
            data-testid="field-tags"
            type="text"
            value={tagInputValue}
            onChange={(e) => setTagInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === ",") {
                e.preventDefault();
                const trimmed = tagInputValue.trim().replace(/,$/, "").trim();
                if (trimmed && !tags.includes(trimmed)) {
                  setTags([...tags, trimmed]);
                }
                setTagInputValue("");
              }
            }}
            placeholder="Type and press Enter to add"
            className="min-h-[44px] flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <button
            type="button"
            data-testid="add-tag-button"
            onClick={() => {
              const trimmed = tagInputValue.trim();
              if (trimmed && !tags.includes(trimmed)) {
                setTags([...tags, trimmed]);
              }
              setTagInputValue("");
            }}
            disabled={!tagInputValue.trim()}
            className="min-h-[44px] rounded-md border border-input bg-background px-3 py-2 text-sm font-medium hover:bg-muted disabled:opacity-50"
          >
            Add
          </button>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <button
          type="submit"
          data-testid="submit-button"
          disabled={isPending || (submitted && hasRequiredEmpty)}
          className="min-h-[44px] rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isPending ? "Saving…" : story ? "Update story" : "Create story"}
        </button>
        <button
          type="button"
          data-testid="cancel-button"
          onClick={onCancel}
          className="min-h-[44px] rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-muted"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
