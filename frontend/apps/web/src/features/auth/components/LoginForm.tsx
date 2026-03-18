"use client";

import { useState } from "react";
import { useForm } from "@tanstack/react-form";
import { z } from "zod";
import { toast } from "sonner";
import { ApiError } from "@reqruit/api-client";
import { useLogin } from "../hooks/useAuth";

const emailSchema = z.string().email("Please enter a valid email");
const passwordSchema = z.string().min(1, "Password is required");

function validateField(schema: z.ZodString, value: string): string | undefined {
  const result = schema.safeParse(value);
  return result.success ? undefined : result.error.issues[0]?.message;
}

interface LoginFormProps {
  redirectTo?: string;
}

export function LoginForm({ redirectTo }: LoginFormProps) {
  const login = useLogin(redirectTo);
  // Form-level error for 401 — do not reveal which field is wrong (AC#2)
  const [formError, setFormError] = useState<string | null>(null);

  const form = useForm({
    defaultValues: { email: "", password: "" },
    onSubmit: async ({ value }) => {
      setFormError(null);
      try {
        await login.mutateAsync({ email: value.email, password: value.password });
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          setFormError("Incorrect email or password");
        } else if (err instanceof ApiError && err.status >= 500) {
          toast.error("Something went wrong — please try again later.");
        } else {
          toast.error("Unable to connect. Please check your network and try again.", { duration: Infinity });
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
      {/* Form-level error — AC#2: single message, no field hints */}
      {formError && (
        <div role="alert" aria-live="assertive">
          {formError}
        </div>
      )}

      {/* Email field */}
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
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => {
                  field.handleChange(e.target.value);
                  setFormError(null);
                }}
                aria-describedby={error ? "login-email-error" : undefined}
                aria-invalid={!!error}
              />
              {error && (
                <span id="login-email-error" role="alert">
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
                autoComplete="current-password"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(e) => {
                  field.handleChange(e.target.value);
                  setFormError(null);
                }}
                aria-describedby={error ? "login-password-error" : undefined}
                aria-invalid={!!error}
              />
              {error && (
                <span id="login-password-error" role="alert">
                  {error}
                </span>
              )}
            </div>
          );
        }}
      </form.Field>

      <button type="submit" disabled={login.isPending}>
        {login.isPending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
