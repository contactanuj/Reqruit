"use client";

import { useState } from "react";
import { useForm } from "@tanstack/react-form";
import { z } from "zod";
import { ApiError } from "@reqruit/api-client";
import { useRegister } from "../hooks/useAuth";

// ---------------------------------------------------------------------------
// Zod schemas (AC#3 — blur validation with spec-exact messages)
// ---------------------------------------------------------------------------

const emailSchema = z.string().email("Please enter a valid email");
const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters");

function validateField(schema: z.ZodString, value: string): string | undefined {
  const result = schema.safeParse(value);
  return result.success ? undefined : result.error.issues[0]?.message;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function RegisterForm() {
  const register = useRegister();
  // Server-side field errors (422 duplicate email — AC#2)
  const [emailServerError, setEmailServerError] = useState<string | null>(null);

  const form = useForm({
    defaultValues: { email: "", password: "", confirmPassword: "" },
    onSubmit: async ({ value }) => {
      setEmailServerError(null);
      try {
        await register.mutateAsync({
          email: value.email,
          password: value.password,
        });
      } catch (err) {
        // 422 → inline field error (AC#2); 502/500/503 handled in useRegister.onError
        if (err instanceof ApiError && err.status === 422) {
          const body = err.data as { detail?: string } | undefined;
          const detail =
            typeof body?.detail === "string"
              ? body.detail
              : "An account with this email already exists";
          setEmailServerError(detail);
        }
      }
    },
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        void form.handleSubmit();
      }}
      noValidate
    >
      {/* Email field */}
      <form.Field
        name="email"
        validators={{
          onChange: () => undefined, // clear error as user types
          onBlur: ({ value }) => validateField(emailSchema, value),
          onSubmit: ({ value }) => validateField(emailSchema, value),
        }}
      >
        {(field) => {
          const fieldError = field.state.meta.errors[0];
          const error = emailServerError ?? (typeof fieldError === "string" ? fieldError : undefined);
          return (
            <div>
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => {
                  field.handleChange(e.target.value);
                  setEmailServerError(null);
                }}
                aria-describedby={error ? "email-error" : undefined}
                aria-invalid={!!error}
              />
              {error && (
                <span id="email-error" role="alert">
                  {error}
                </span>
              )}
            </div>
          );
        }}
      </form.Field>

      {/* Password field */}
      <form.Field
        name="password"
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
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => field.handleChange(e.target.value)}
                aria-describedby={error ? "password-error" : undefined}
                aria-invalid={!!error}
              />
              {error && (
                <span id="password-error" role="alert">
                  {error}
                </span>
              )}
            </div>
          );
        }}
      </form.Field>

      {/* Confirm password field */}
      <form.Field
        name="confirmPassword"
        validators={{
          onChange: () => undefined,
          onBlur: ({ value, fieldApi }) => {
            const password = fieldApi.form.state.values.password;
            return value !== password ? "Passwords do not match" : undefined;
          },
          onSubmit: ({ value, fieldApi }) => {
            const password = fieldApi.form.state.values.password;
            return value !== password ? "Passwords do not match" : undefined;
          },
        }}
      >
        {(field) => {
          const fieldError = field.state.meta.errors[0];
          const error = typeof fieldError === "string" ? fieldError : undefined;
          return (
            <div>
              <label htmlFor="confirmPassword">Confirm Password</label>
              <input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => field.handleChange(e.target.value)}
                aria-describedby={error ? "confirmPassword-error" : undefined}
                aria-invalid={!!error}
              />
              {error && (
                <span id="confirmPassword-error" role="alert">
                  {error}
                </span>
              )}
            </div>
          );
        }}
      </form.Field>

      <button type="submit" disabled={register.isPending}>
        {register.isPending ? "Creating account…" : "Create account"}
      </button>
    </form>
  );
}
