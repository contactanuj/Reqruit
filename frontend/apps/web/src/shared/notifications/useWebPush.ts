// useWebPush.ts — Web Push API integration (FE-8.4)
// Handles subscribing/unsubscribing to browser push notifications.

import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@reqruit/api-client";

export type PushPermission = "default" | "granted" | "denied";

export interface WebPushHook {
  isSupported: boolean;
  isSubscribed: boolean;
  permission: PushPermission;
  subscribe: () => Promise<void>;
  unsubscribe: () => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export function useWebPush(): WebPushHook {
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isSupported =
    typeof window !== "undefined" &&
    "Notification" in window &&
    "serviceWorker" in navigator &&
    "PushManager" in window;

  const [permission, setPermission] = useState<PushPermission>(() =>
    isSupported ? (Notification.permission as PushPermission) : "default",
  );

  // Check existing subscription on mount
  useEffect(() => {
    if (!isSupported) return;

    navigator.serviceWorker.ready
      .then((reg) => reg.pushManager.getSubscription())
      .then((sub) => setIsSubscribed(sub !== null))
      .catch(() => setIsSubscribed(false));
  }, [isSupported]);

  const subscribe = useCallback(async () => {
    if (!isSupported) return;
    setIsLoading(true);
    setError(null);

    try {
      const reg = await navigator.serviceWorker.ready;
      const vapidKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ?? "";

      const subscribeOptions: PushSubscriptionOptionsInit = {
        userVisibleOnly: true,
      };
      if (vapidKey) {
        subscribeOptions.applicationServerKey = urlBase64ToUint8Array(vapidKey);
      }

      const subscription = await reg.pushManager.subscribe(subscribeOptions);

      await apiClient.post("/notifications/subscribe", subscription.toJSON());
      setIsSubscribed(true);
      setPermission(Notification.permission as PushPermission);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to subscribe to push notifications";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [isSupported]);

  const unsubscribe = useCallback(async () => {
    if (!isSupported) return;
    setIsLoading(true);
    setError(null);

    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        await sub.unsubscribe();
        await apiClient.delete("/notifications/subscribe");
      }
      setIsSubscribed(false);
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to unsubscribe from push notifications";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [isSupported]);

  return {
    isSupported,
    isSubscribed,
    permission,
    subscribe,
    unsubscribe,
    isLoading,
    error,
  };
}
