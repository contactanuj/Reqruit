"use client";

import { useState } from "react";
import { useForm } from "@tanstack/react-form";
import { z } from "zod";
import { toast } from "sonner";
import { ApiError } from "@reqruit/api-client";
import { useProfile, useUpdateEmail, useUpdatePassword } from "../hooks/useAuth";

const emailSchema = z.string().email("Please enter a valid email");
const passwordSchema = z.string().min(8, "Password must be at least 8 characters");

function validateField(schema: z.ZodString, value: string): string | undefined {
  const result = schema.safeParse(value);
  return result.success ? undefined : result.error.issues[0]?.message;
}

// ---------------------------------------------------------------------------
// Change Email Form
// ---------------------------------------------------------------------------

function ChangeEmailForm() {
  const updateEmail = useUpdateEmail();

  const form = useForm({
    defaultValues: { email: "" },
    onSubmit: async ({ value }) => {
      try {
        await updateEmail.mutateAsync({ email: value.email });
        form.reset();
      } catch (err) {
        if (err instanceof ApiError && err.status === 422) {
          const body = err.data as { detail?: string } | undefined;
          toast.error(body?.detail ?? "This email is already in use");
        } else {
          toast.error("Failed to update email — please try again later");
        }
      }
    },
  });

  return (
    <section aria-labelledby="change-email-heading">
      <h2 id="change-email-heading">Change email</h2>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void form.handleSubmit();
        }}
        noValidate
      >
        <form.Field
          name="email"
          validators={{
            onChange: () => undefined,
            onBlur: ({ value }) => validateField(emailSchema, value),
            onSubmit: ({ value }) => validateField(emailSchema, value),
          }}
        >
          {(field) => {
            const fieldError = field.state.meta.errors[0];
            const error = typeof fieldError === "string" ? fieldError : undefined;
            return (
              <div>
                <label htmlFor="new-email">New email</label>
                <input
                  id="new-email"
                  type="email"
                  autoComplete="email"
                  value={field.state.value}
                  onBlur={field.handleBlur}
                  onChange={(e) => field.handleChange(e.target.value)}
                  aria-describedby={error ? "new-email-error" : undefined}
                  aria-invalid={!!error}
                />
                {error && (
                  <span id="new-email-error" role="alert">
                    {error}
                  </span>
                )}
              </div>
            );
          }}
        </form.Field>

        <button type="submit" disabled={updateEmail.isPending}>
          {updateEmail.isPending ? "Updating…" : "Update email"}
        </button>
      </form>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Change Password Form
// ---------------------------------------------------------------------------

function ChangePasswordForm() {
  const updatePassword = useUpdatePassword();
  const [currentPasswordError, setCurrentPasswordError] = useState<string | null>(null);

  const form = useForm({
    defaultValues: { currentPassword: "", newPassword: "", confirmPassword: "" },
    onSubmit: async ({ value }) => {
      setCurrentPasswordError(null);
      try {
        await updatePassword.mutateAsync({
          current_password: value.currentPassword,
          new_password: value.newPassword,
        });
        form.reset();
      } catch (err) {
        if (err instanceof ApiError && (err.status === 422 || err.status === 401)) {
          setCurrentPasswordError("Current password is incorrect");
        }
      }
    },
  });

  return (
    <section aria-labelledby="change-password-heading">
      <h2 id="change-password-heading">Change password</h2>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void form.handleSubmit();
        }}
        noValidate
      >
        {/* Current password */}
        <form.Field name="currentPassword">
          {(field) => (
            <div>
              <label htmlFor="current-password">Current password</label>
              <input
                id="current-password"
                type="password"
                autoComplete="current-password"
                value={field.state.value}
                onChange={(e) => {
                  field.handleChange(e.target.value);
                  setCurrentPasswordError(null);
                }}
                aria-describedby={currentPasswordError ? "current-password-error" : undefined}
                aria-invalid={!!currentPasswordError}
              />
              {currentPasswordError && (
                <span id="current-password-error" role="alert">
                  {currentPasswordError}
                </span>
              )}
            </div>
          )}
        </form.Field>

        {/* New password */}
        <form.Field
          name="newPassword"
          validators={{
            onChange: () => undefined,
            onBlur: ({ value }) => validateField(passwordSchema, value),
            onSubmit: ({ value }) => validateField(passwordSchema, value),
          }}
        >
          {(field) => {
            const fieldError = field.state.meta.errors[0];
            const error = typeof fieldError === "string" ? fieldError : undefined;
            return (
              <div>
                <label htmlFor="new-password">New password</label>
                <input
                  id="new-password"
                  type="password"
                  autoComplete="new-password"
                  value={field.state.value}
                  onBlur={field.handleBlur}
                  onChange={(e) => field.handleChange(e.target.value)}
                  aria-describedby={error ? "new-password-error" : undefined}
                  aria-invalid={!!error}
                />
                {error && (
                  <span id="new-password-error" role="alert">
                    {error}
                  </span>
                )}
              </div>
            );
          }}
        </form.Field>

        {/* Confirm password — cross-field validation against newPassword */}
        <form.Field
          name="confirmPassword"
          validators={{
            onChange: () => undefined,
            onBlur: ({ value, fieldApi }) => {
              const newPassword = fieldApi.form.getFieldValue("newPassword");
              return value !== newPassword ? "Passwords do not match" : undefined;
            },
            onSubmit: ({ value, fieldApi }) => {
              const newPassword = fieldApi.form.getFieldValue("newPassword");
              return value !== newPassword ? "Passwords do not match" : undefined;
            },
          }}
        >
          {(field) => {
            const fieldError = field.state.meta.errors[0];
            const error = typeof fieldError === "string" ? fieldError : undefined;
            return (
              <div>
                <label htmlFor="confirm-new-password">Confirm new password</label>
                <input
                  id="confirm-new-password"
                  type="password"
                  autoComplete="new-password"
                  value={field.state.value}
                  onBlur={field.handleBlur}
                  onChange={(e) => field.handleChange(e.target.value)}
                  aria-describedby={error ? "confirm-password-error" : undefined}
                  aria-invalid={!!error}
                />
                {error && (
                  <span id="confirm-password-error" role="alert">
                    {error}
                  </span>
                )}
              </div>
            );
          }}
        </form.Field>

        <button type="submit" disabled={updatePassword.isPending}>
          {updatePassword.isPending ? "Updating…" : "Update password"}
        </button>
      </form>
    </section>
  );
}

// ---------------------------------------------------------------------------
// AccountSettingsForm — composed form
// ---------------------------------------------------------------------------

function CurrentEmailDisplay() {
  const { data: user, isPending } = useProfile();

  return (
    <div className="mb-4">
      <label className="text-sm font-medium text-muted-foreground">Current email</label>
      {isPending ? (
        <p className="text-sm text-muted-foreground mt-1">Loading…</p>
      ) : (
        <p className="text-sm text-foreground mt-1" data-testid="current-email">
          {user?.email ?? "—"}
        </p>
      )}
    </div>
  );
}

export function AccountSettingsForm() {
  return (
    <div>
      <CurrentEmailDisplay />
      <ChangeEmailForm />
      <ChangePasswordForm />
    </div>
  );
}
