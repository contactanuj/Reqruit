"use client";

// OfflineBanner — FE-9.2
// Displays an accessible banner when the user is offline.
// Appears within 1 second of connection loss; dismisses on reconnect.
// Distinguishes between "showing cached data" and "no cached data available".

import { useState, useEffect } from "react";
import { WifiOff } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

export function OfflineBanner() {
  const [isOffline, setIsOffline] = useState(() =>
    typeof navigator !== "undefined" ? !navigator.onLine : false
  );
  const queryClient = useQueryClient();

  useEffect(() => {
    const handleOffline = () => setIsOffline(true);
    const handleOnline = () => setIsOffline(false);

    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);

    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
    };
  }, []);

  if (!isOffline) return null;

  // Check if there is any cached query data available
  const queryCache = queryClient.getQueryCache();
  const hasCachedData = queryCache.getAll().some(
    (query) => query.state.data !== undefined
  );

  const message = hasCachedData
    ? "You're offline \u2014 showing cached data"
    : "No cached data available \u2014 connect to the internet to get started";

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="fixed top-0 inset-x-0 z-50 flex items-center justify-center gap-2 bg-amber-500 px-4 py-2 text-sm font-medium text-white shadow-md"
      data-testid="offline-banner"
    >
      <WifiOff className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}
