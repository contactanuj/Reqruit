"use client";

// ContactsList.tsx — Job contacts management (FE-5.7)

import { useState, useCallback } from "react";
import { toast } from "sonner";
import { useFocusTrap } from "@repo/ui/hooks";
import { useJobContacts, useAddContact, useDeleteContact } from "../hooks/useJobDetail";
import type { AddContactPayload, ContactRoleType } from "../types";

interface ContactsListProps {
  jobId: string;
}

const ROLE_TYPE_COLORS: Record<ContactRoleType, string> = {
  Recruiter: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  Engineer: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  "Hiring Manager": "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
  Generic: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300",
};

export function ContactsList({ jobId }: ContactsListProps) {
  const { data: contacts, isPending } = useJobContacts(jobId);
  const addContact = useAddContact(jobId, () => setShowForm(false));
  const deleteContact = useDeleteContact(jobId);

  const [showForm, setShowForm] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const handleCancelDeleteDialog = useCallback(() => {
    setConfirmDeleteId(null);
  }, []);

  const { dialogRef: deleteDialogRef, handleBackdropClick: handleDeleteBackdropClick } =
    useFocusTrap({ open: confirmDeleteId !== null, onClose: handleCancelDeleteDialog });

  // Form state
  const [name, setName] = useState("");
  const [roleType, setRoleType] = useState<ContactRoleType>("Generic");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [email, setEmail] = useState("");
  const [linkedinError, setLinkedinError] = useState("");

  function resetForm() {
    setName("");
    setRoleType("Generic");
    setLinkedinUrl("");
    setEmail("");
    setLinkedinError("");
  }

  function validateLinkedin(url: string): boolean {
    if (!url) return true;
    return url.startsWith("https://linkedin.com/in/") || url.startsWith("https://www.linkedin.com/in/");
  }

  function handleAdd() {
    if (!name.trim()) return;
    if (!validateLinkedin(linkedinUrl)) {
      setLinkedinError("LinkedIn URL must start with https://linkedin.com/in/");
      return;
    }
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast.error("Please enter a valid email address");
      return;
    }

    const payload: AddContactPayload = {
      name: name.trim(),
      role_type: roleType,
      linkedin_url: linkedinUrl.trim() || undefined,
      email: email.trim() || undefined,
    };

    addContact.mutate(payload, {
      onSuccess: () => {
        resetForm();
      },
    });
  }

  function handleDelete(contactId: string) {
    deleteContact.mutate(contactId, {
      onSuccess: () => {
        setConfirmDeleteId(null);
      },
      onError: () => {
        setConfirmDeleteId(null);
        toast.error("Failed to delete contact — please try again");
      },
    });
  }

  if (isPending) {
    return (
      <div className="flex flex-col gap-2 animate-pulse" aria-hidden="true">
        {Array.from({ length: 2 }, (_, i) => (
          <div key={i} className="h-12 rounded bg-muted" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4" data-testid="contacts-list">
      {/* Contacts list */}
      {contacts && contacts.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {contacts.map((contact) => (
            <li
              key={contact.id}
              className="flex items-start justify-between rounded-lg border border-border p-3"
            >
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{contact.name}</span>
                  <span
                    className={[
                      "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                      ROLE_TYPE_COLORS[contact.role_type],
                    ].join(" ")}
                  >
                    {contact.role_type}
                  </span>
                </div>
                {contact.linkedin_url && (
                  <a
                    href={contact.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary underline hover:no-underline"
                  >
                    LinkedIn
                  </a>
                )}
                {contact.email && (
                  <span className="text-xs text-muted-foreground">{contact.email}</span>
                )}
              </div>
              <button
                type="button"
                onClick={() => setConfirmDeleteId(contact.id)}
                className="text-xs text-red-600 hover:text-red-700"
                aria-label={`Delete contact ${contact.name}`}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">No contacts added yet.</p>
      )}

      {/* Add contact button */}
      {!showForm && (
        <button
          type="button"
          onClick={() => setShowForm(true)}
          className="self-start rounded-md border border-border px-3 py-1.5 text-sm hover:bg-muted/50 transition-colors"
        >
          + Add contact
        </button>
      )}

      {/* Add contact form */}
      {showForm && (
        <div className="flex flex-col gap-3 rounded-lg border border-border p-4">
          <h4 className="text-sm font-semibold">New contact</h4>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium" htmlFor="contact-name">
              Name <span aria-hidden="true">*</span>
            </label>
            <input
              id="contact-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium" htmlFor="contact-role">
              Role type
            </label>
            <select
              id="contact-role"
              value={roleType}
              onChange={(e) => setRoleType(e.target.value as ContactRoleType)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="Recruiter">Recruiter</option>
              <option value="Engineer">Engineer</option>
              <option value="Hiring Manager">Hiring Manager</option>
              <option value="Generic">Generic</option>
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium" htmlFor="contact-linkedin">
              LinkedIn URL
            </label>
            <input
              id="contact-linkedin"
              type="url"
              value={linkedinUrl}
              onChange={(e) => {
                setLinkedinUrl(e.target.value);
                setLinkedinError("");
              }}
              placeholder="https://linkedin.com/in/…"
              className="rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
            {linkedinError && (
              <p className="text-xs text-red-600" role="alert">{linkedinError}</p>
            )}
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium" htmlFor="contact-email">
              Email
            </label>
            <input
              id="contact-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => {
                resetForm();
                setShowForm(false);
              }}
              className="rounded-md border border-border px-3 py-1.5 text-sm"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleAdd}
              disabled={addContact.isPending || !name.trim()}
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
            >
              {addContact.isPending ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      )}

      {/* Delete confirmation dialog — focus-trapped, Escape/backdrop to close */}
      {confirmDeleteId && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={handleDeleteBackdropClick}
        >
          <div
            ref={deleteDialogRef}
            role="alertdialog"
            aria-label="Delete contact"
            aria-modal="true"
            className="w-full max-w-xs rounded-lg bg-background border border-border p-6 shadow-lg"
          >
            <h3 className="text-base font-semibold mb-2">Delete this contact?</h3>
            <p className="text-sm text-muted-foreground mb-4">This action cannot be undone.</p>
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                onClick={() => setConfirmDeleteId(null)}
                className="rounded-md border border-border px-3 py-1.5 text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleDelete(confirmDeleteId)}
                className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white"
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
