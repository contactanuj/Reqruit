// service-worker.ts — Serwist service worker configuration (FE-9.1, FE-8.4)
// Handles precaching, push notifications, and notification click events.
// This file is the Serwist-based service worker entry point.

import { defaultCache } from "@serwist/next/worker";
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import { Serwist } from "serwist";

// Serwist types
declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: ServiceWorkerGlobalScope & {
  __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
};

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: defaultCache,
});

serwist.addEventListeners();

// ---------------------------------------------------------------------------
// Push notification handler (FE-8.4)
// No PII in payloads — only notification ID and type (NFR-S3)
// ---------------------------------------------------------------------------

self.addEventListener("push", (event) => {
  if (!event.data) return;

  const data = event.data.json() as {
    title?: string;
    body?: string;
    icon?: string;
    notificationId?: string;
    type?: string;
    route?: string;
  };

  const title = data.title ?? "Reqruit";
  const options: NotificationOptions = {
    body: data.body ?? "You have a new notification",
    icon: data.icon ?? "/icons/icon-192.webp",
    badge: "/icons/icon-192.webp",
    tag: data.notificationId ?? "reqruit-notification",
    data: { route: data.route ?? "/" },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// ---------------------------------------------------------------------------
// Notification click handler (FE-8.4)
// ---------------------------------------------------------------------------

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const route = (event.notification.data as { route?: string })?.route ?? "/";

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        for (const client of clientList) {
          if ("focus" in client) {
            void client.focus();
            if ("navigate" in client) {
              void (client as WindowClient).navigate(route);
            }
            return;
          }
        }
        return self.clients.openWindow(route);
      })
  );
});
