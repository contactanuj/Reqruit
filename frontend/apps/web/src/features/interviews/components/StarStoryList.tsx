"use client";

// StarStoryList.tsx — FE-11.1 STAR story library list view

import * as React from "react";
import DOMPurify from "dompurify";
import {
  useStarStoriesQuery,
  useCreateStarStory,
  useUpdateStarStory,
  useDeleteStarStory,
} from "../hooks/useStarStories";
import { StarStoryForm } from "./StarStoryForm";
import type { StarStory, StarStoryFormData } from "../types";

const MAX_SITUATION_LENGTH = 120;

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max).trimEnd() + "...";
}

export function StarStoryList() {
  const { data: stories, isLoading, error } = useStarStoriesQuery();
  const createMutation = useCreateStarStory();
  const updateMutation = useUpdateStarStory();
  const deleteMutation = useDeleteStarStory();

  // null = list view, "new" = create form, string id = edit form
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = React.useState<{
    id: string;
    title: string;
  } | null>(null);

  function handleCreate(data: StarStoryFormData) {
    createMutation.mutate(data, {
      onSuccess: () => setEditingId(null),
    });
  }

  function handleUpdate(id: string, data: StarStoryFormData) {
    updateMutation.mutate(
      { id, data },
      { onSuccess: () => setEditingId(null) },
    );
  }

  function handleDeleteConfirm() {
    if (!deleteTarget) return;
    deleteMutation.mutate(deleteTarget.id);
    setDeleteTarget(null);
  }

  // Loading state
  if (isLoading) {
    return (
      <div data-testid="loading-state" className="py-12 text-center">
        <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <p className="mt-2 text-sm text-muted-foreground">
          Loading STAR stories…
        </p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        data-testid="star-story-list"
        className="rounded-md border border-red-300 bg-red-50 px-4 py-6 text-center text-sm text-red-700 dark:border-red-700 dark:bg-red-900/20 dark:text-red-400"
        role="alert"
      >
        Failed to load STAR stories. Please try again later.
      </div>
    );
  }

  // Show create form
  if (editingId === "new") {
    return (
      <div data-testid="star-story-list">
        <h2 className="mb-4 text-lg font-semibold">New STAR Story</h2>
        <StarStoryForm
          onSubmit={handleCreate}
          onCancel={() => setEditingId(null)}
          isPending={createMutation.isPending}
        />
      </div>
    );
  }

  // Show edit form
  if (editingId && stories) {
    const story = stories.find((s) => s.id === editingId);
    if (story) {
      return (
        <div data-testid="star-story-list">
          <h2 className="mb-4 text-lg font-semibold">Edit STAR Story</h2>
          <StarStoryForm
            story={story}
            onSubmit={(data) => handleUpdate(story.id, data)}
            onCancel={() => setEditingId(null)}
            isPending={updateMutation.isPending}
          />
        </div>
      );
    }
  }

  // Empty state
  if (!stories || stories.length === 0) {
    return (
      <div data-testid="star-story-list">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">STAR Stories</h2>
          <button
            type="button"
            data-testid="add-story-button"
            onClick={() => setEditingId("new")}
            className="min-h-[44px] rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Add story
          </button>
        </div>
        <div
          data-testid="empty-state"
          className="rounded-md border border-dashed border-muted-foreground/30 px-4 py-12 text-center"
        >
          <p className="text-sm text-muted-foreground">
            No STAR stories yet. Add your first story to prepare for
            interviews.
          </p>
        </div>
      </div>
    );
  }

  // List view
  return (
    <div data-testid="star-story-list">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">STAR Stories</h2>
        <button
          type="button"
          data-testid="add-story-button"
          onClick={() => setEditingId("new")}
          className="min-h-[44px] rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Add story
        </button>
      </div>

      <ul className="space-y-3" role="list">
        {stories.map((story: StarStory) => (
          <li
            key={story.id}
            data-testid={`star-story-card-${story.id}`}
            className="rounded-md border border-border bg-card p-4"
            role="article"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-semibold text-card-foreground">
                  {DOMPurify.sanitize(story.title)}
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {DOMPurify.sanitize(truncate(story.situation, MAX_SITUATION_LENGTH))}
                </p>
                {story.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {story.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                      >
                        {DOMPurify.sanitize(tag)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="flex shrink-0 gap-1">
                <button
                  type="button"
                  data-testid={`edit-story-${story.id}`}
                  onClick={() => setEditingId(story.id)}
                  aria-label={`Edit ${story.title}`}
                  className="min-h-[44px] min-w-[44px] rounded-md border border-input bg-background px-2 py-1 text-xs font-medium hover:bg-muted"
                >
                  Edit
                </button>
                <button
                  type="button"
                  data-testid={`delete-story-${story.id}`}
                  onClick={() => setDeleteTarget({ id: story.id, title: story.title })}
                  aria-label={`Delete ${story.title}`}
                  className="min-h-[44px] min-w-[44px] rounded-md border border-red-300 bg-background px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/30"
                >
                  Delete
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {/* Delete confirmation dialog */}
      {deleteTarget && (
        <div
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="delete-dialog-title"
          aria-describedby="delete-dialog-desc"
          data-testid="delete-confirm-dialog"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onKeyDown={(e) => {
            if (e.key === "Escape") setDeleteTarget(null);
          }}
        >
          <div className="mx-4 w-full max-w-sm rounded-lg border border-border bg-background p-6 shadow-lg">
            <h2
              id="delete-dialog-title"
              className="text-base font-semibold text-foreground"
            >
              Delete STAR Story
            </h2>
            <p
              id="delete-dialog-desc"
              className="mt-2 text-sm text-muted-foreground"
            >
              Delete &ldquo;{deleteTarget.title}&rdquo;? This cannot be undone.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                data-testid="delete-cancel-button"
                onClick={() => setDeleteTarget(null)}
                className="min-h-[44px] rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-muted"
                autoFocus
              >
                Cancel
              </button>
              <button
                type="button"
                data-testid="delete-confirm-button"
                onClick={handleDeleteConfirm}
                className="min-h-[44px] rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
