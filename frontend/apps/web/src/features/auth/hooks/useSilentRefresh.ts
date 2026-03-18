"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { signOut } from "next-auth/react";
import { useAuthStore } from "../store/auth-store";

const REFRESH_THRESHOLD_MS = 60_000; // Refresh 60s before expiry
const MIN_REFRESH_DELAY_MS = 5_000; // Minimum 5s between refreshes to prevent loops

const getBaseUrl = (): string =>
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Parse the `exp` (Unix timestamp) from a JWT payload. Returns null if token is invalid. */
export function getTokenExpiry(token: string): number | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(
      atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"))
    ) as { exp?: number };
    return typeof payload.exp === "number" ? payload.exp : null;
  } catch {
    return null;
  }
}

/**
 * Proactively refreshes the access token 60s before expiry (AC#1).
 * Clears auth and redirects to /login on refresh failure (AC#2).
 * Also triggers on tab focus if token is near expiry (AC#1).
 */
export function useSilentRefresh(): void {
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const setAccessToken = useAuthStore((s) => s.setAccessToken);
  const clearAuth = useAuthStore((s) => s.clearAuth);

  useEffect(() => {
    if (!accessToken) return;

    const exp = getTokenExpiry(accessToken);
    if (exp === null) return;

    const nowMs = Date.now();
    const expiryMs = exp * 1000;
    const delay = Math.max(MIN_REFRESH_DELAY_MS, expiryMs - nowMs - REFRESH_THRESHOLD_MS);

    async function performRefresh() {
      try {
        const response = await fetch(`${getBaseUrl()}/auth/refresh`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });

        if (!response.ok) {
          clearAuth();
          await signOut({ redirect: false });
          router.push("/login");
          return;
        }

        const data = (await response.json()) as { access_token: string };
        setAccessToken(data.access_token);
      } catch {
        clearAuth();
        await signOut({ redirect: false });
        router.push("/login");
      }
    }

    const timerId = setTimeout(() => void performRefresh(), delay);

    function handleVisibilityChange() {
      if (document.visibilityState !== "visible") return;
      const currentToken = useAuthStore.getState().accessToken;
      if (!currentToken) return;
      const currentExp = getTokenExpiry(currentToken);
      if (currentExp === null) return;
      const msUntilExpiry = currentExp * 1000 - Date.now();
      if (msUntilExpiry < REFRESH_THRESHOLD_MS) {
        void performRefresh();
      }
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      clearTimeout(timerId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [accessToken, clearAuth, setAccessToken, router]);
}
