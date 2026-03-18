"use client";

// AppShell.tsx — Three-panel layout shell for all authenticated routes (FE-2.1)
// Panels: Sidebar (220px|56px) + Content (fluid) + AICopilotPanel (320px)
// Uses CSS logical properties exclusively (ms-/me-/ps-/pe-).

import { useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/shared/layouts/Sidebar";
import { BottomNav } from "@/shared/layouts/BottomNav";
import { AICopilotPanel } from "@/shared/layouts/AICopilotPanel";
import { OfflineBanner } from "@/shared/layouts/OfflineBanner";
import { DemoBanner } from "@/shared/layouts/DemoBanner";
import { CommandPalette } from "@repo/ui/components";
import { KeyboardShortcutsOverlay } from "@repo/ui/components";
import { useKeyboardShortcuts } from "@repo/ui/hooks";
import { useLayoutStore } from "@/features/shell/store/layout-store";
import type { CommandItem } from "@repo/ui/components";

const NAV_COMMANDS: CommandItem[] = [
  {
    id: "nav-dashboard",
    label: "Dashboard",
    category: "navigation",
    action: () => {},
  },
  { id: "nav-jobs", label: "Jobs", category: "navigation", action: () => {} },
  {
    id: "nav-applications",
    label: "Applications",
    category: "navigation",
    action: () => {},
  },
  {
    id: "nav-profile",
    label: "Profile",
    category: "navigation",
    action: () => {},
  },
  {
    id: "nav-settings",
    label: "Settings",
    category: "navigation",
    action: () => {},
  },
];

const AI_COMMANDS_TEMPLATE: Omit<CommandItem, "action">[] = [
  {
    id: "ai-cover-letter",
    label: "Generate cover letter",
    category: "ai-action",
  },
  {
    id: "ai-research",
    label: "Research company",
    category: "ai-action",
  },
  {
    id: "ai-skills",
    label: "Analyse skills gap",
    category: "ai-action",
  },
];

const AI_COMMAND_ROUTES: Record<string, string> = {
  "ai-cover-letter": "/applications",
  "ai-research": "/jobs",
  "ai-skills": "/profile",
};

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const {
    commandPaletteOpen,
    setCommandPaletteOpen,
    shortcutsOverlayVisible,
    setSidebarCollapsed,
    setShortcutsOverlayVisible,
  } = useLayoutStore();

  const openCommandPalette = useCallback(
    () => setCommandPaletteOpen(true),
    [setCommandPaletteOpen],
  );
  const closeCommandPalette = useCallback(
    () => setCommandPaletteOpen(false),
    [setCommandPaletteOpen],
  );

  // Load recent items from localStorage
  const recentItems: CommandItem[] = useMemo(() => {
    try {
      const stored = localStorage.getItem("reqruit-recent-commands");
      return stored ? JSON.parse(stored).slice(0, 5) : [];
    } catch {
      return [];
    }
  }, []);

  // Build command items with real router actions
  const navCommands: CommandItem[] = useMemo(
    () =>
      NAV_COMMANDS.map((c) => ({
        ...c,
        action: () => {
          router.push(`/${c.id.replace("nav-", "")}`);
        },
      })),
    [router],
  );

  // Build AI commands with real router actions
  const aiCommands: CommandItem[] = useMemo(
    () =>
      AI_COMMANDS_TEMPLATE.map((c) => ({
        ...c,
        action: () => {
          router.push(AI_COMMAND_ROUTES[c.id] ?? "/");
        },
      })),
    [router],
  );

  // Merge recent items + nav + AI commands
  const commands: CommandItem[] = useMemo(
    () => [
      ...recentItems.map((item) => ({ ...item, category: "recent" as const })),
      ...navCommands,
      ...aiCommands,
    ],
    [recentItems, navCommands, aiCommands],
  );

  const handleCommandExecute = useCallback(
    (item: CommandItem) => {
      // Save to recent
      try {
        const stored = JSON.parse(
          localStorage.getItem("reqruit-recent-commands") || "[]",
        );
        const filtered = stored.filter((r: CommandItem) => r.id !== item.id);
        const updated = [
          { id: item.id, label: item.label, category: item.category },
          ...filtered,
        ].slice(0, 5);
        localStorage.setItem(
          "reqruit-recent-commands",
          JSON.stringify(updated),
        );
      } catch {
        // Ignore localStorage errors
      }
      // Execute the command
      item.action?.();
      setCommandPaletteOpen(false);
    },
    [setCommandPaletteOpen],
  );

  // Keyboard shortcuts
  useKeyboardShortcuts([
    // Command palette
    {
      key: "k",
      meta: true,
      description: "Open command palette",
      action: openCommandPalette,
    },
    // Shortcuts overlay
    {
      key: "?",
      description: "Show keyboard shortcuts",
      action: () => setShortcutsOverlayVisible(true),
    },
    // Sidebar
    {
      key: "[",
      description: "Collapse sidebar",
      action: () => setSidebarCollapsed(true),
    },
    {
      key: "]",
      description: "Expand sidebar",
      action: () => setSidebarCollapsed(false),
    },
    // Navigation chords: G + letter
    {
      key: "g",
      chord: "d",
      description: "Go to Dashboard",
      action: () => router.push("/dashboard"),
    },
    {
      key: "g",
      chord: "j",
      description: "Go to Jobs",
      action: () => router.push("/jobs"),
    },
    {
      key: "g",
      chord: "a",
      description: "Go to Applications",
      action: () => router.push("/applications"),
    },
    {
      key: "g",
      chord: "p",
      description: "Go to Profile",
      action: () => router.push("/profile"),
    },
    {
      key: "g",
      chord: "s",
      description: "Go to Settings",
      action: () => router.push("/settings"),
    },
    // Focus Kanban search when on applications page
    {
      key: "/",
      description: "Focus search",
      action: () => {
        if (window.location.pathname.includes("/applications")) {
          const searchInput = document.querySelector<HTMLInputElement>("[data-kanban-search]");
          searchInput?.focus();
        }
      },
    },
  ]);

  return (
    <>
      {/* Offline banner (FE-9.2) */}
      <OfflineBanner />

      {/* Demo mode banner (FE-9.4) */}
      <DemoBanner />

      {/* Three-panel shell — full viewport height */}
      <div
        data-testid="app-shell"
        className="flex h-screen overflow-hidden bg-background"
      >
        {/* Left: Sidebar (desktop) */}
        <Sidebar />

        {/* Centre: Main content + bottom padding for mobile nav */}
        <main
          className="flex-1 overflow-y-auto min-w-0 md:min-w-[480px] pb-16 md:pb-0"
          aria-label="Main content"
        >
          {children}
        </main>

        {/* Right: AI Copilot panel (≥1024px) */}
        <AICopilotPanel />
      </div>

      {/* Mobile: fixed bottom nav (≤767px) */}
      <BottomNav />

      {/* Global overlays */}
      <CommandPalette
        open={commandPaletteOpen}
        onClose={closeCommandPalette}
        items={commands}
        onSelect={handleCommandExecute}
      />

      <KeyboardShortcutsOverlay
        open={shortcutsOverlayVisible}
        onClose={() => setShortcutsOverlayVisible(false)}
      />
    </>
  );
}
