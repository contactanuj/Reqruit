// useDemoSession.ts — Demo sandbox session management (FE-9.4)
// Fetches demo user tokens and sets isDemoMode flag in auth store.

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@reqruit/api-client";
import { useAuthStore } from "../store/auth-store";

interface DemoSessionResponse {
  access_token: string;
}

export function useDemoSession() {
  const router = useRouter();
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const setDemoMode = useAuthStore((s) => s.setDemoMode);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const isDemoMode = useAuthStore((s) => s.isDemoMode);

  /**
   * Start demo session: call GET /auth/demo-session, store tokens, redirect to dashboard.
   * Throws on failure so the caller can display an error UI.
   */
  const startDemoSession = useCallback(async () => {
    const data = await apiClient.get<DemoSessionResponse>("/auth/demo-session");
    setAccessToken(data.access_token);
    setDemoMode(true);
    router.push("/dashboard");
  }, [setAccessToken, setDemoMode, router]);

  /**
   * End demo session: clear auth store and redirect to register.
   * Demo sessions don't use NextAuth, so no signOut() call is needed.
   */
  const endDemoSession = useCallback(() => {
    clearAuth();
    router.push("/register");
  }, [clearAuth, router]);

  return {
    isDemoMode,
    startDemoSession,
    endDemoSession,
  };
}
