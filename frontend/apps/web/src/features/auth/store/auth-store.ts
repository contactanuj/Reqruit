import { create } from "zustand";

// Access token stored in memory ONLY — never localStorage or cookies (NFR-S1)
// Refresh token is in httpOnly cookie managed by NextAuth v5

interface AuthState {
  accessToken: string | null;
  isAuthenticated: boolean;
  /** True when running in demo sandbox mode (FE-9.4) */
  isDemoMode: boolean;
  setAccessToken: (token: string) => void;
  clearAuth: () => void;
  setDemoMode: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  isAuthenticated: false,
  isDemoMode: false,
  setAccessToken: (token: string) =>
    set({ accessToken: token, isAuthenticated: true }),
  clearAuth: () =>
    set({ accessToken: null, isAuthenticated: false, isDemoMode: false }),
  setDemoMode: (value: boolean) => set({ isDemoMode: value }),
}));
