import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";

// Routes that require authentication
const PROTECTED_PREFIXES = ["/dashboard", "/jobs", "/applications", "/profile", "/settings", "/admin"];
// Routes only for unauthenticated users
const AUTH_ROUTES = ["/login", "/register"];
// Public routes accessible without authentication (FE-9.4)
const PUBLIC_ROUTES = ["/demo"];

const NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_HOSTNAME = new URL(NEXT_PUBLIC_API_URL).hostname;

function buildCspHeader(nonce: string): string {
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self'",
    `connect-src 'self' ${NEXT_PUBLIC_API_URL} wss://${API_HOSTNAME}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}

/** Apply CSP header to a response. */
function withCsp(response: NextResponse, cspHeader: string): NextResponse {
  response.headers.set("Content-Security-Policy", cspHeader);
  return response;
}

export async function middleware(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const cspHeader = buildCspHeader(nonce);

  // Clone request headers — Next.js reads CSP from request headers to extract the nonce
  // and automatically applies it to all framework-injected <script> tags during SSR.
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("Content-Security-Policy", cspHeader);
  requestHeaders.set("x-nonce", nonce);

  const { pathname } = request.nextUrl;

  // Public routes — skip all auth checks (FE-9.4)
  if (PUBLIC_ROUTES.some((route) => pathname.startsWith(route))) {
    return withCsp(
      NextResponse.next({ request: { headers: requestHeaders } }),
      cspHeader,
    );
  }

  // Check for auth token cookie (set by NextAuth)
  const hasSession = request.cookies.has("next-auth.session-token") ||
    request.cookies.has("__Secure-next-auth.session-token");

  const isProtectedRoute = PROTECTED_PREFIXES.some((prefix) =>
    pathname.startsWith(prefix)
  );
  const isAuthRoute = AUTH_ROUTES.some((route) => pathname === route);

  if (isProtectedRoute && !hasSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return withCsp(NextResponse.redirect(loginUrl), cspHeader);
  }

  // Admin route guard — require admin role
  if (pathname.startsWith("/admin") && hasSession) {
    const token = await getToken({ req: request });
    if (!token || token.role !== "admin") {
      return withCsp(NextResponse.redirect(new URL("/dashboard", request.url)), cspHeader);
    }
  }

  if (isAuthRoute && hasSession) {
    return withCsp(NextResponse.redirect(new URL("/dashboard", request.url)), cspHeader);
  }

  // Prevent browser from caching authenticated pages — blocks back-nav after logout (AC#2)
  if (isProtectedRoute && hasSession) {
    const response = NextResponse.next({ request: { headers: requestHeaders } });
    response.headers.set("Cache-Control", "no-store");
    return withCsp(response, cspHeader);
  }

  return withCsp(
    NextResponse.next({ request: { headers: requestHeaders } }),
    cspHeader,
  );
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|manifest.json|sw.js).*)",
  ],
};
