"use client";

// ApplicationNotes.tsx — Inline notes panel for an application (FE-6.3)
// Notes are plain text — rendered as React text children (no HTML injection risk).

import { useState, KeyboardEvent } from "react";
import { useApplicationNotes, useAddNote, useUpdateNote } from "../hooks/useKanban";
import type { ApplicationNote } from "../types";

interface ApplicationNotesProps {
  applicationId: string;
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function isEdited(note: ApplicationNote): boolean {
  return note.updated_at !== note.created_at;
}

export function ApplicationNotes({ applicationId }: ApplicationNotesProps) {
  const { data: notes, isPending } = useApplicationNotes(applicationId);
  const addNote = useAddNote(applicationId);
  const updateNote = useUpdateNote(applicationId);

  const [addingNote, setAddingNote] = useState(false);
  const [newNoteContent, setNewNoteContent] = useState("");
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");

  function handleAddSave() {
    const trimmed = newNoteContent.trim();
    if (!trimmed) return;
    addNote.mutate(
      { content: trimmed },
      {
        onSuccess: () => {
          setNewNoteContent("");
          setAddingNote(false);
        },
      }
    );
  }

  function handleAddKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleAddSave();
    }
  }

  function handleEditSave(noteId: string) {
    const trimmed = editContent.trim();
    if (!trimmed) return;
    updateNote.mutate(
      { noteId, content: trimmed },
      {
        onSuccess: () => {
          setEditingNoteId(null);
          setEditContent("");
        },
      }
    );
  }

  function handleEditKeyDown(e: KeyboardEvent<HTMLTextAreaElement>, noteId: string) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleEditSave(noteId);
    }
  }

  function startEditing(note: ApplicationNote) {
    setEditingNoteId(note.id);
    setEditContent(note.content);
  }

  return (
    <section aria-label="Application notes" className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Notes</h3>
        {!addingNote && (
          <button
            type="button"
            onClick={() => setAddingNote(true)}
            className="text-xs text-primary hover:underline"
            aria-label="Add a new note"
          >
            + Add note
          </button>
        )}
      </div>

      {/* New note form */}
      {addingNote && (
        <div className="flex flex-col gap-2" data-testid="add-note-form">
          <textarea
            value={newNoteContent}
            onChange={(e) => setNewNoteContent(e.target.value)}
            onKeyDown={handleAddKeyDown}
            placeholder="Type your note… (Cmd+Enter to save)"
            className="w-full rounded-md border border-border bg-background p-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
            rows={3}
            autoFocus
            aria-label="Note content"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleAddSave}
              disabled={addNote.isPending}
              className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              data-testid="save-note-btn"
            >
              {addNote.isPending ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              onClick={() => {
                setAddingNote(false);
                setNewNoteContent("");
              }}
              className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-muted"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Existing notes */}
      {isPending ? (
        <div className="space-y-2">
          {[1, 2].map((i) => (
            <div key={i} className="h-12 rounded-md bg-muted animate-pulse" aria-hidden="true" />
          ))}
        </div>
      ) : (
        <ul className="flex flex-col gap-2" aria-label="Notes list">
          {(notes ?? []).map((note) => (
            <li
              key={note.id}
              className="rounded-md border border-border bg-card p-2.5 text-sm"
              data-testid="note-item"
            >
              {editingNoteId === note.id ? (
                <div className="flex flex-col gap-2">
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    onKeyDown={(e) => handleEditKeyDown(e, note.id)}
                    className="w-full rounded-md border border-border bg-background p-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                    rows={3}
                    aria-label="Edit note content"
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => handleEditSave(note.id)}
                      disabled={updateNote.isPending}
                      className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                    >
                      {updateNote.isPending ? "Saving…" : "Save"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingNoteId(null)}
                      className="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-muted"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {/* Plain text note content — no HTML rendering needed */}
                  <p className="text-sm text-foreground mb-1 whitespace-pre-wrap">
                    {note.content}
                  </p>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <time dateTime={note.created_at}>
                        {formatTimestamp(note.created_at)}
                      </time>
                      {isEdited(note) && (
                        <span
                          className="rounded bg-muted px-1.5 py-0.5 text-xs"
                          aria-label={`Edited on ${formatTimestamp(note.updated_at)}`}
                          data-testid="edited-badge"
                        >
                          Edited
                        </span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => startEditing(note)}
                      className="text-xs text-muted-foreground hover:text-foreground hover:underline"
                      aria-label={`Edit note from ${formatTimestamp(note.created_at)}`}
                    >
                      Edit
                    </button>
                  </div>
                </>
              )}
            </li>
          ))}
          {(notes?.length ?? 0) === 0 && !addingNote && (
            <li className="text-xs text-muted-foreground py-2 text-center">
              No notes yet
            </li>
          )}
        </ul>
      )}
    </section>
  );
}
