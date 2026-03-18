// All API calls MUST go through this typed client — never raw fetch() with string URLs (ARCH-6)
// API types are auto-generated from FastAPI OpenAPI spec (ARCH-7)

const getBaseUrl = (): string => {
  if (typeof window === "undefined") {
    // Server-side (SSR / Route Handlers): prefer internal URL to avoid external network round-trip
    return process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  }
  // Client-side: use public env var (available at build time)
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
};

// ---------------------------------------------------------------------------
// 401 Auth Interceptor (NFR-R3 — Tier 1 error handling)
// Callbacks are injected by the app layer to avoid circular dependencies.
// ---------------------------------------------------------------------------

interface AuthInterceptorConfig {
  getAccessToken: () => string | null;
  setAccessToken: (token: string) => void;
  onAuthFailed: () => void;
}

let authInterceptor: AuthInterceptorConfig | null = null;
let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

/** Call once at app startup (e.g., in QueryProvider) to wire up 401 auto-refresh. */
export function configureAuth(config: AuthInterceptorConfig): void {
  authInterceptor = config;
}

/** Attempts a silent token refresh using the httpOnly refresh cookie. */
async function refreshAccessToken(): Promise<string | null> {
  try {
    const response = await fetch(`${getBaseUrl()}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) return null;
    const data = (await response.json()) as { access_token: string };
    return data.access_token ?? null;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  token?: string;
  /** Internal flag: prevents recursive 401 retry after refresh. */
  _skipRefresh?: boolean;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data: unknown
  ) {
    super(`API error ${status}: ${statusText}`);
    this.name = "ApiError";
  }
}

// ---------------------------------------------------------------------------
// Core request function
// ---------------------------------------------------------------------------

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, headers = {}, _skipRefresh = false } = options;

  // Use explicit token, then fall back to Zustand memory store
  const token = options.token ?? authInterceptor?.getAccessToken() ?? undefined;

  const requestHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...headers,
  };

  if (token) {
    requestHeaders["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${getBaseUrl()}${path}`, {
    method,
    headers: requestHeaders,
    credentials: "include", // Required for httpOnly refresh token cookie (NFR-S1)
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // ---------------------------------------------------------------------------
  // 401 interceptor — silent refresh + retry (AC#3 / NFR-R3)
  // Skip: auth endpoints, already-retried requests, no interceptor configured
  // ---------------------------------------------------------------------------
  if (
    response.status === 401 &&
    authInterceptor &&
    !_skipRefresh &&
    path !== "/auth/refresh" &&
    path !== "/auth/login" &&
    path !== "/auth/register"
  ) {
    if (isRefreshing) {
      // Another request is already refreshing — wait for it, then retry
      const newToken = await refreshPromise;
      if (newToken) {
        return request<T>(path, { ...options, token: newToken, _skipRefresh: true });
      }
      authInterceptor.onAuthFailed();
      throw new ApiError(401, "Session expired", {});
    }

    isRefreshing = true;
    refreshPromise = refreshAccessToken();
    const newToken = await refreshPromise;
    // Defer nulling refreshPromise to the next microtask so concurrent waiters
    // that are already awaiting it can resolve before the reference disappears.
    void Promise.resolve().then(() => {
      isRefreshing = false;
      refreshPromise = null;
    });

    if (newToken) {
      authInterceptor.setAccessToken(newToken);
      return request<T>(path, { ...options, token: newToken, _skipRefresh: true });
    }

    // Refresh failed — clear auth and redirect
    authInterceptor.onAuthFailed();
    throw new ApiError(401, response.statusText, {});
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, response.statusText, data);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Multipart upload function (for file uploads — no JSON Content-Type)
// ---------------------------------------------------------------------------

async function uploadRequest<T>(path: string, formData: FormData, token?: string): Promise<T> {
  const accessToken = token ?? authInterceptor?.getAccessToken() ?? undefined;

  const headers: Record<string, string> = {};
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const response = await fetch(`${getBaseUrl()}${path}`, {
    method: "POST",
    headers,
    credentials: "include",
    body: formData,
  });

  if (
    response.status === 401 &&
    authInterceptor &&
    path !== "/auth/refresh"
  ) {
    if (isRefreshing) {
      const newToken = await refreshPromise;
      if (newToken) {
        return uploadRequest<T>(path, formData, newToken);
      }
      authInterceptor.onAuthFailed();
      throw new ApiError(401, "Session expired", {});
    }

    isRefreshing = true;
    refreshPromise = refreshAccessToken();
    const newToken = await refreshPromise;
    // Defer nulling refreshPromise to the next microtask so concurrent waiters
    // that are already awaiting it can resolve before the reference disappears.
    void Promise.resolve().then(() => {
      isRefreshing = false;
      refreshPromise = null;
    });

    if (newToken) {
      authInterceptor.setAccessToken(newToken);
      return uploadRequest<T>(path, formData, newToken);
    }

    authInterceptor.onAuthFailed();
    throw new ApiError(401, response.statusText, {});
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, response.statusText, data);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Public API client
// ---------------------------------------------------------------------------

export const apiClient = {
  get: <T>(path: string, token?: string) =>
    request<T>(path, { method: "GET", token }),

  post: <T>(path: string, body: unknown, token?: string) =>
    request<T>(path, { method: "POST", body, token }),

  patch: <T>(path: string, body: unknown, token?: string) =>
    request<T>(path, { method: "PATCH", body, token }),

  put: <T>(path: string, body: unknown, token?: string) =>
    request<T>(path, { method: "PUT", body, token }),

  delete: <T>(path: string, token?: string) =>
    request<T>(path, { method: "DELETE", token }),

  /**
   * Upload a file via multipart/form-data (ARCH-6 compliant).
   * Skips JSON Content-Type header so the browser sets the correct boundary.
   */
  upload: <T>(path: string, formData: FormData, token?: string) =>
    uploadRequest<T>(path, formData, token),
};
