// Wire up the 401 auto-refresh interceptor in the api-client.
// Runs at module-load time — import this file from the root client provider.
// Uses Zustand's getState() to avoid React hook constraints (outside render cycle).

import { configureAuth } from "@reqruit/api-client";
import { useAuthStore } from "@/features/auth/store/auth-store";

configureAuth({
  getAccessToken: () => useAuthStore.getState().accessToken,
  setAccessToken: (token) => useAuthStore.getState().setAccessToken(token),
  onAuthFailed: () => {
    useAuthStore.getState().clearAuth();
    if (typeof window !== "undefined") {
      window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
    }
  },
});
