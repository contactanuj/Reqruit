// AppShell layout — wraps all authenticated routes (FE-2.1)

import { AuthProvider } from "@/shared/providers/AuthProvider";
import { ThemeProvider } from "@/shared/providers/ThemeProvider";
import { AppShell } from "@/shared/layouts/AppShell";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <ThemeProvider>
        <AppShell>{children}</AppShell>
      </ThemeProvider>
    </AuthProvider>
  );
}
