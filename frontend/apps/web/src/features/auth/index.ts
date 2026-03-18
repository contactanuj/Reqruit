// Public API for the auth feature — no cross-feature deep imports allowed
export { RegisterForm } from "./components/RegisterForm";
export { LoginForm } from "./components/LoginForm";
export { AccountSettingsForm } from "./components/AccountSettingsForm";
export { useRegister, useLogin, useLogout, useProfile, useUpdateEmail, useUpdatePassword } from "./hooks/useAuth";
export { useSilentRefresh } from "./hooks/useSilentRefresh";
export { useAuthStore } from "./store/auth-store";
export type { RegisterRequest, LoginRequest, AuthTokenResponse, UpdateEmailRequest, UpdatePasswordRequest, UserProfile } from "./types";
