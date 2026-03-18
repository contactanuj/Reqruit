import type { Metadata } from "next";
import { headers } from "next/headers";
import { Inter } from "next/font/google";
import { Toaster } from "sonner";
import { QueryProvider } from "@/shared/providers/QueryProvider";
import { NextAuthProvider } from "@/shared/providers/NextAuthProvider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Reqruit — AI Job Hunting Assistant",
  description: "Your AI-powered job hunting assistant",
  manifest: "/manifest.json",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const headersList = await headers();
  const nonce = headersList.get("x-nonce") ?? "";

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Blocking script to prevent FOUC when dark mode is persisted */}
        <script
          nonce={nonce}
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=JSON.parse(localStorage.getItem('theme-store')||'{}');var r=t&&t.state&&t.state.theme;if(r==='dark'||(!r&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}})();`,
          }}
        />
      </head>
      <body className={inter.variable}>
        <NextAuthProvider>
          <QueryProvider>{children}</QueryProvider>
        </NextAuthProvider>
        <Toaster />
      </body>
    </html>
  );
}
