// useAuth.ts — registration and authentication mutations
// AC Rule: no boolean loading state; use isPending from useMutation (Rule 4)
// Auth Rule: access token → Zustand memory only; refresh token → httpOnly cookie (NFR-S1)

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { signIn, signOut } from "next-auth/react";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import { useAuthStore } from "../store/auth-store";
import type {
  RegisterRequest,
  LoginRequest,
  AuthTokenResponse,
  UserProfile,
  UpdateEmailRequest,
  UpdatePasswordRequest,
} from "../types";

/** Remove the persisted TanStack Query cache from IndexedDB to prevent data leakage on logout. */
async function clearPersistedCache(): Promise<void> {
  try {
    const db = await new Promise<IDBDatabase>((resolve, reject) => {
      const req = indexedDB.open("reqruit-cache", 1);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    const tx = db.transaction("query-cache", "readwrite");
    tx.objectStore("query-cache").delete("reqruit-query-cache");
    db.close();
  } catch {
    // IndexedDB may be unavailable (SSR, private browsing) — silently ignore
  }
}

// ---------------------------------------------------------------------------
// useRegister
// ---------------------------------------------------------------------------

export function useRegister() {
  const router = useRouter();
  const setAccessToken = useAuthStore((s) => s.setAccessToken);

  return useMutation<AuthTokenResponse, ApiError, RegisterRequest>({
    mutationFn: (data) =>
      apiClient.post<AuthTokenResponse>("/auth/register", data),

    onSuccess: async (data) => {
      // Store in memory — never localStorage (NFR-S1)
      setAccessToken(data.access_token);
      // Create NextAuth session (sets next-auth.session-token httpOnly cookie)
      await signIn("credentials", {
        accessToken: data.access_token,
        redirect: false,
      });
      router.push("/onboarding");
    },

    onError: (error) => {
      // 502: service-level toast (Tier 2 — UX-17 persistent+retry variant)
      if (error.status === 502) {
        toast.error(
          "Service temporarily unavailable — please try again in a moment",
          { duration: Infinity }
        );
      } else if (error.status === 500 || error.status === 503) {
        // 500/503: generic server error toast
        toast.error("Something went wrong — please try again later");
      }
      // 422: handled at component level (field-level error, Tier 3)
    },
  });
}

// ---------------------------------------------------------------------------
// useLogin
// ---------------------------------------------------------------------------

export function useLogin(redirectTo?: string) {
  const router = useRouter();
  const setAccessToken = useAuthStore((s) => s.setAccessToken);

  return useMutation<AuthTokenResponse, ApiError, LoginRequest>({
    mutationFn: (data) =>
      apiClient.post<AuthTokenResponse>("/auth/login", data),

    onSuccess: async (data) => {
      setAccessToken(data.access_token);
      await signIn("credentials", {
        accessToken: data.access_token,
        redirect: false,
      });
      router.push(redirectTo ?? "/dashboard");
    },

    // 401 "Incorrect email or password" is handled at component level (form-level error)
    // No toast needed here — 401 on login is an expected user error
  });
}

// ---------------------------------------------------------------------------
// useLogout
// ---------------------------------------------------------------------------

export function useLogout() {
  const router = useRouter();
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, void>({
    mutationFn: () => apiClient.post<void>("/auth/logout", {}),

    onSuccess: async () => {
      // Clear all cached user data from memory (prevents data leakage)
      queryClient.clear();
      // Clear persisted query cache in IndexedDB to prevent data leakage to next user
      void clearPersistedCache();
      // Clear Zustand in-memory access token
      clearAuth();
      // Remove NextAuth session cookie (httpOnly refresh token)
      await signOut({ redirect: false });
      router.push("/login");
    },

    onError: async () => {
      // Clear local state even if server logout fails (network error, 500, etc.)
      queryClient.clear();
      void clearPersistedCache();
      clearAuth();
      await signOut({ redirect: false });
      router.push("/login");
    },
  });
}

// ---------------------------------------------------------------------------
// useProfile — fetches current user profile
// ---------------------------------------------------------------------------

export function useProfile() {
  return useQuery<UserProfile, ApiError>({
    queryKey: queryKeys.profile.me(),
    queryFn: () => apiClient.get<UserProfile>("/users/me"),
  });
}

// ---------------------------------------------------------------------------
// useUpdateEmail
// ---------------------------------------------------------------------------

export function useUpdateEmail() {
  const queryClient = useQueryClient();

  return useMutation<UserProfile, ApiError, UpdateEmailRequest>({
    mutationFn: (data) => apiClient.patch<UserProfile>("/users/me", data),

    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.profile.me() });
      toast.success("Email updated successfully");
    },
  });
}

// ---------------------------------------------------------------------------
// useUpdatePassword
// ---------------------------------------------------------------------------

export function useUpdatePassword() {
  return useMutation<void, ApiError, UpdatePasswordRequest>({
    mutationFn: (data) => apiClient.patch<void>("/users/me", data),
    // Wrong current password (422) handled at component level as inline field error
  });
}
