"use client";

import { useEffect } from "react";
import { useSession } from "next-auth/react";
import { useAuthStore } from "@/features/auth/store/auth-store";
import { useSilentRefresh } from "@/features/auth/hooks/useSilentRefresh";

/**
 * Syncs the NextAuth session access token → Zustand auth store on page load / session change (AC#3).
 * Also mounts the silent refresh hook for proactive token renewal (AC#1, #2).
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession();
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const clearAuth = useAuthStore((s) => s.clearAuth);

  // Restore access token from NextAuth session on page reload (AC#3)
  useEffect(() => {
    if (session?.accessToken) {
      setAccessToken(session.accessToken);
    } else if (session === null) {
      // session === null means definitely unauthenticated (not loading)
      clearAuth();
    }
  }, [session, setAccessToken, clearAuth]);

  // Proactive silent refresh (AC#1, #2)
  useSilentRefresh();

  return <>{children}</>;
}
