// NextAuth v5 configuration
// Credentials provider bridges our custom FastAPI JWT with NextAuth session cookies.
// Access token lives in memory (Zustand); refresh token in httpOnly cookie from FastAPI.
// NextAuth session cookie (next-auth.session-token) is used by middleware for auth checks.

import NextAuth from "next-auth";
import type { NextAuthConfig } from "next-auth";
import Credentials from "next-auth/providers/credentials";

// Extend NextAuth types to include accessToken and expiry tracking
declare module "next-auth" {
  interface User {
    accessToken?: string;
    expiresAt?: number;
  }
  interface Session {
    accessToken?: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    refreshToken?: string;
    expiresAt?: number;
  }
}

/** Decode the `exp` claim from a JWT without verifying signature (server-side only). */
function decodeTokenExp(token: string): number | undefined {
  try {
    const payload = JSON.parse(Buffer.from(token.split(".")[1]!, "base64url").toString());
    return typeof payload.exp === "number" ? payload.exp * 1000 : undefined;
  } catch {
    return undefined;
  }
}

export const config: NextAuthConfig = {
  providers: [
    Credentials({
      credentials: {
        accessToken: {},
      },
      authorize: async (credentials) => {
        const { accessToken } = credentials as { accessToken?: string };
        if (!accessToken) return null;
        // Trust the token — it was just issued by our FastAPI backend
        return { id: "session", accessToken };
      },
    }),
  ],

  callbacks: {
    jwt: async ({ token, user }) => {
      if (user?.accessToken) {
        token.accessToken = user.accessToken;
        token.expiresAt = user.expiresAt ?? decodeTokenExp(user.accessToken);
      }

      // Server-side: if token is expired, return null to force client-side refresh.
      // Server-side fetch cannot carry the browser's httpOnly refresh cookie,
      // so attempting a refresh here is futile — let the client handle it.
      if (token.expiresAt && Date.now() >= (token.expiresAt as number) - 60_000) {
        return { ...token, accessToken: undefined, expiresAt: undefined };
      }

      return token;
    },
    session: ({ session, token }) => {
      session.accessToken = token.accessToken;
      return session;
    },
  },

  pages: {
    signIn: "/login",
    error: "/login",
  },

  // Trust cookies sent over http in development
  trustHost: true,
};

export const { handlers, signIn, signOut, auth } = NextAuth(config);
