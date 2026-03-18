"use client";

// Settings → Account page
// Displays current email and provides forms to update email and password (AC#1 — FE-1.6)

import { AccountSettingsForm } from "@/features/auth";

export default function AccountSettingsPage() {
  return (
    <main>
      <h1>Account settings</h1>
      <AccountSettingsForm />
    </main>
  );
}
