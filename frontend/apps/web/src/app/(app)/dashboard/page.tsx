// Dashboard page — FE-8.1, FE-8.2, FE-8.3, FE-8.5, FE-8.6
// Main dashboard with morning briefing, XP widget (mobile), nudge cards, activity section.

import { MorningBriefingCard } from "@/features/dashboard/components/MorningBriefingCard";
import { NudgeCardList } from "@/features/dashboard/components/NudgeCardList";
import { XPWidget } from "@/features/gamification/components/XPWidget";
import { ActivityHeatmapSection } from "@/features/gamification/components/ActivityHeatmapSection";
import { UpgradePrompt } from "@/features/credits/components/UpgradePrompt";

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Mobile: XP widget in dashboard header (desktop uses Sidebar) */}
      <div className="md:hidden">
        <XPWidget />
      </div>

      {/* Low credits upgrade prompt */}
      <UpgradePrompt />

      {/* Morning briefing */}
      <MorningBriefingCard />

      {/* Nudge cards */}
      <section>
        <h2 className="text-lg font-semibold mb-3">Recommended actions</h2>
        <NudgeCardList />
      </section>

      {/* Activity section */}
      <ActivityHeatmapSection />
    </div>
  );
}
