// Gamification types for FE-14

export interface LeaderboardEntry {
  userId: string;
  username: string;
  weeklyXp: number;
  rank: number;
  isCurrentUser: boolean;
}

export interface LeaderboardData {
  entries: LeaderboardEntry[];
  currentUserEntry?: LeaderboardEntry;
  lastWeekWinner?: { username: string; xp: number };
}

export interface SprintGoal {
  id: string;
  description: string;
  targetCount: number;
  currentCount: number;
}

export interface Sprint {
  id: string;
  startDate: string;
  endDate: string;
  goals: SprintGoal[];
  status: "active" | "completed";
  retrospective?: string;
}
