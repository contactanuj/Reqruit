// Admin feature types (FE-15)

export interface LocaleConfig {
  locale: string;
  currencySymbol: string;
  salaryRangeMin: number;
  salaryRangeMax: number;
  jobBoardSources: string[];
  noticePeriodDefault: number;
}

export interface DiscoverySource {
  id: string;
  name: string;
  lastSyncTime: string;
  status: "healthy" | "degraded" | "failed";
}

export type TaskStatus = "pending" | "running" | "failed" | "completed";

export interface BackgroundTask {
  id: string;
  type: string;
  status: TaskStatus;
  createdAt: string;
  logs?: string;
}

export interface PiiEvent {
  id: string;
  timestamp: string;
  eventType: string;
  contentSnippet: string;
  userId: string;
  status: "pending" | "confirmed" | "false_positive";
}

export interface CostAnalytics {
  totalSpend: number;
  dailyTrend: { date: string; cost: number }[];
  topUsersByCost: CostEntry[];
  topAgentsByCost: CostEntry[];
}

export interface CostEntry {
  id: string;
  name: string;
  totalCost: number;
  isAnomaly: boolean;
}

export interface UserCostDetail {
  userId: string;
  dailyCosts: { date: string; cost: number }[];
}
