// use-pwa.ts — PWA installation hook (FE-9.1)
// Captures beforeinstallprompt and exposes promptInstall() function.

import { useState, useEffect, useCallback } from "react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export interface PWAHook {
  canInstall: boolean;
  isInstalled: boolean;
  isIOS: boolean;
  isStandalone: boolean;
  promptInstall: () => Promise<void>;
}

export function usePWA(): PWAHook {
  const [installPrompt, setInstallPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [isInstalled, setIsInstalled] = useState(false);

  const [isStandalone, setIsStandalone] = useState(() =>
    typeof window !== "undefined" &&
    window.matchMedia("(display-mode: standalone)").matches
  );

  const isIOS =
    typeof navigator !== "undefined" &&
    /iPad|iPhone|iPod/.test(navigator.userAgent) &&
    !(window as unknown as { MSStream?: unknown }).MSStream;

  // Keep isStandalone reactive via matchMedia change listener
  useEffect(() => {
    const mql = window.matchMedia("(display-mode: standalone)");
    const handler = (e: MediaQueryListEvent) => setIsStandalone(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setInstallPrompt(e as BeforeInstallPromptEvent);
    };

    window.addEventListener("beforeinstallprompt", handler);

    const appInstalledHandler = () => {
      setIsInstalled(true);
      setInstallPrompt(null);
    };
    window.addEventListener("appinstalled", appInstalledHandler);

    // Check if already installed
    if (isStandalone) {
      setIsInstalled(true);
    }

    return () => {
      window.removeEventListener("beforeinstallprompt", handler);
      window.removeEventListener("appinstalled", appInstalledHandler);
    };
  }, [isStandalone]);

  const promptInstall = useCallback(async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    const choice = await installPrompt.userChoice;
    if (choice.outcome === "accepted") {
      setIsInstalled(true);
    }
    setInstallPrompt(null);
  }, [installPrompt]);

  return {
    canInstall: installPrompt !== null && !isInstalled,
    isInstalled,
    isIOS,
    isStandalone,
    promptInstall,
  };
}
