// Query key factory — ALL TanStack Query cache keys must come from here (Rule 1)
// No inline query key arrays permitted anywhere in the codebase
//
// ── ARCH-20 Per-Query Stale Time Policy ──────────────────────────────────
// Domain             staleTime       Notes
// ─────────────────  ──────────────  ─────────────────────────────────────
// Jobs (list/detail) 5 min (300_000) Listings change infrequently
// Kanban board       30s (30_000)    Reflects real-time pipeline movement
// Profile            1 hr (3_600_000) Rarely changes within a session
// Company research   1 hr (3_600_000) Static once fetched
// Morning briefing   15 min (900_000) Fresh each morning, stale by midday
// Default (global)   1 min (60_000)  Set in QueryProvider defaultOptions
// ──────────────────────────────────────────────────────────────────────────
// Apply per-query staleTime in the relevant useQuery/queryOptions call,
// e.g.: useQuery({ queryKey: queryKeys.jobs.list(), staleTime: 300_000 })

export const queryKeys = {
  auth: {
    all: ["auth"] as const,
    me: () => [...queryKeys.auth.all, "me"] as const,
  },
  profile: {
    all: ["profile"] as const,
    detail: (userId: string) => [...queryKeys.profile.all, userId] as const,
    resume: (userId: string) => [...queryKeys.profile.all, userId, "resume"] as const,
    versions: (userId: string) => [...queryKeys.profile.all, userId, "versions"] as const,
    skillAnalysis: (userId: string) => [...queryKeys.profile.all, userId, "skill-analysis"] as const,
    // Profile feature keys (FE-4)
    me: () => [...queryKeys.profile.all, "me"] as const,
    resumeStatus: (resumeId: string) => [...queryKeys.profile.all, "resume-status", resumeId] as const,
    resumes: () => [...queryKeys.profile.all, "resumes"] as const,
    // skillAnalysisMe removed — use skillAnalysis("me") consistently
  },
  jobs: {
    all: ["jobs"] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.jobs.all, "list", filters] as const,
    detail: (jobId: string) => [...queryKeys.jobs.all, jobId] as const,
    shortlist: () => [...queryKeys.jobs.all, "shortlist"] as const,
    contacts: (jobId: string) => [...queryKeys.jobs.all, jobId, "contacts"] as const,
    companyResearch: (jobId: string) => [...queryKeys.jobs.all, jobId, "company"] as const,
  },
  applications: {
    all: ["applications"] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.applications.all, "list", filters] as const,
    detail: (appId: string) => [...queryKeys.applications.all, appId] as const,
    notes: (appId: string) => [...queryKeys.applications.all, appId, "notes"] as const,
    stats: () => [...queryKeys.applications.all, "stats"] as const,
    assemblyStatus: (appId: string) =>
      [...queryKeys.applications.all, appId, "assembly-status"] as const,
  },
  documents: {
    all: ["documents"] as const,
    list: (appId: string) => [...queryKeys.documents.all, appId] as const,
    detail: (docId: string) => [...queryKeys.documents.all, docId] as const,
    versions: (appId: string) => [...queryKeys.documents.all, appId, "versions"] as const,
    coverLetters: (appId: string) => ["documents", "cover-letters", appId] as const,
  },
  outreach: {
    all: ["outreach"] as const,
    list: (jobId: string) => [...queryKeys.outreach.all, jobId] as const,
    detail: (jobId: string, contactId: string) =>
      [...queryKeys.outreach.all, jobId, contactId] as const,
  },
  interview: {
    all: ["interview"] as const,
    starStories: () => [...queryKeys.interview.all, "star-stories"] as const,
    sessions: (appId: string) => [...queryKeys.interview.all, "sessions", appId] as const,
    questions: (appId: string) => [...queryKeys.interview.all, "questions", appId] as const,
    mockSessions: () => [...queryKeys.interview.all, "mock-sessions"] as const,
    transcript: (sessionId: string) =>
      [...queryKeys.interview.all, "mock-sessions", sessionId, "transcript"] as const,
  },
  offers: {
    all: ["offers"] as const,
    list: () => [...queryKeys.offers.all, "list"] as const,
    detail: (offerId: string) => [...queryKeys.offers.all, offerId] as const,
    comparison: (offerIds: string[]) => [...queryKeys.offers.all, "compare", ...offerIds] as const,
  },
  dashboard: {
    all: ["dashboard"] as const,
    briefing: () => [...queryKeys.dashboard.all, "briefing"] as const,
    morningBriefing: () => [...queryKeys.dashboard.all, "morning-briefing"] as const,
    nudges: () => [...queryKeys.dashboard.all, "nudges"] as const,
  },
  usage: {
    all: ["usage"] as const,
    credits: () => [...queryKeys.usage.all, "credits"] as const,
    history: () => [...queryKeys.usage.all, "history"] as const,
  },
  credits: {
    all: ["credits"] as const,
    usage: () => [...queryKeys.credits.all, "usage"] as const,
  },
  gamification: {
    all: ["gamification"] as const,
    stats: () => [...queryKeys.gamification.all, "stats"] as const,
    status: () => [...queryKeys.gamification.all, "status"] as const,
    league: () => [...queryKeys.gamification.all, "league"] as const,
    heatmap: () => [...queryKeys.gamification.all, "heatmap"] as const,
    activityHistory: () => [...queryKeys.gamification.all, "activity-history"] as const,
    leaderboard: () => [...queryKeys.gamification.all, "leaderboard"] as const,
    sprints: () => [...queryKeys.gamification.all, "sprints"] as const,
    sprintDetail: (sprintId: string) => [...queryKeys.gamification.all, "sprints", sprintId] as const,
  },
  notifications: {
    all: ["notifications"] as const,
    preferences: () => [...queryKeys.notifications.all, "preferences"] as const,
  },
  admin: {
    all: ["admin"] as const,
    localeConfig: () => [...queryKeys.admin.all, "locale-config"] as const,
    discoverySources: () => [...queryKeys.admin.all, "discovery-sources"] as const,
    tasks: () => [...queryKeys.admin.all, "tasks"] as const,
    taskLogs: (taskId: string) => [...queryKeys.admin.all, "tasks", taskId, "logs"] as const,
    piiEvents: () => [...queryKeys.admin.all, "pii-events"] as const,
    costAnalytics: () => [...queryKeys.admin.all, "cost-analytics"] as const,
    userCosts: (userId: string) => [...queryKeys.admin.all, "costs", userId] as const,
  },
  career: {
    all: ["career"] as const,
    onboardingPlan: (planId: string) => [...queryKeys.career.all, "onboarding", planId] as const,
    wellness: () => [...queryKeys.career.all, "wellness"] as const,
    wellnessTrend: () => [...queryKeys.career.all, "wellness", "trend"] as const,
    pathProjections: () => [...queryKeys.career.all, "path-projections"] as const,
  },
} as const;
