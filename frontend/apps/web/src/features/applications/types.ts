// Application feature types (FE-6)

export type ApplicationStatus =
  | "Saved"
  | "Applied"
  | "Interviewing"
  | "Offered"
  | "Accepted"
  | "Rejected"
  | "Withdrawn";

export const KANBAN_COLUMNS: { status: ApplicationStatus; label: string; color: string }[] = [
  { status: "Saved", label: "Saved", color: "bg-slate-100 text-slate-700" },
  { status: "Applied", label: "Applied", color: "bg-blue-100 text-blue-700" },
  { status: "Interviewing", label: "Interviewing", color: "bg-yellow-100 text-yellow-700" },
  { status: "Offered", label: "Offered", color: "bg-green-100 text-green-700" },
  { status: "Accepted", label: "Accepted", color: "bg-emerald-100 text-emerald-700" },
  { status: "Rejected", label: "Rejected", color: "bg-red-100 text-red-700" },
  { status: "Withdrawn", label: "Withdrawn", color: "bg-gray-100 text-gray-700" },
];

// Valid status transitions (FE-6.2)
// Terminal states: Accepted, Rejected, Withdrawn — no valid outgoing transitions
export const VALID_TRANSITIONS: Record<ApplicationStatus, ApplicationStatus[]> = {
  Saved: ["Applied", "Withdrawn"],
  Applied: ["Interviewing", "Rejected", "Withdrawn"],
  Interviewing: ["Offered", "Rejected", "Withdrawn"],
  Offered: ["Accepted", "Rejected", "Withdrawn"],
  Accepted: [],
  Rejected: [],
  Withdrawn: [],
};

// Human-readable messages for blocked transitions
export const TRANSITION_BLOCK_MESSAGES: Partial<Record<string, string>> = {
  "Saved→Interviewing":
    "Must pass through Applied first before moving to Interviewing.",
  "Saved→Offered":
    "Must pass through Applied and Interviewing before reaching Offered.",
  "Saved→Accepted":
    "Must pass through Applied, Interviewing, and Offered before Accepted.",
  "Saved→Rejected":
    "Move to Applied first, then mark as Rejected if needed.",
  "Applied→Offered":
    "Must pass through Interviewing before reaching Offered.",
  "Applied→Accepted":
    "Must pass through Interviewing and Offered before Accepted.",
  "Interviewing→Accepted":
    "Must receive an Offer before marking as Accepted.",
  "Accepted→Saved":
    "Accepted is a terminal state — no further transitions are allowed.",
  "Accepted→Applied":
    "Accepted is a terminal state — no further transitions are allowed.",
  "Accepted→Interviewing":
    "Accepted is a terminal state — no further transitions are allowed.",
  "Accepted→Offered":
    "Accepted is a terminal state — no further transitions are allowed.",
  "Accepted→Rejected":
    "Accepted is a terminal state — no further transitions are allowed.",
  "Accepted→Withdrawn":
    "Accepted is a terminal state — no further transitions are allowed.",
  "Rejected→Saved":
    "Rejected is a terminal state — no further transitions are allowed.",
  "Rejected→Applied":
    "Rejected is a terminal state — no further transitions are allowed.",
  "Rejected→Interviewing":
    "Rejected is a terminal state — no further transitions are allowed.",
  "Rejected→Offered":
    "Rejected is a terminal state — no further transitions are allowed.",
  "Rejected→Accepted":
    "Rejected is a terminal state — no further transitions are allowed.",
  "Rejected→Withdrawn":
    "Rejected is a terminal state — no further transitions are allowed.",
  "Withdrawn→Saved":
    "Withdrawn is a terminal state — no further transitions are allowed.",
  "Withdrawn→Applied":
    "Withdrawn is a terminal state — no further transitions are allowed.",
  "Withdrawn→Interviewing":
    "Withdrawn is a terminal state — no further transitions are allowed.",
  "Withdrawn→Offered":
    "Withdrawn is a terminal state — no further transitions are allowed.",
  "Withdrawn→Accepted":
    "Withdrawn is a terminal state — no further transitions are allowed.",
  "Withdrawn→Rejected":
    "Withdrawn is a terminal state — no further transitions are allowed.",
};

export function isValidTransition(from: ApplicationStatus, to: ApplicationStatus): boolean {
  return VALID_TRANSITIONS[from].includes(to);
}

export function getTransitionBlockMessage(
  from: ApplicationStatus,
  to: ApplicationStatus
): string {
  const key = `${from}→${to}`;
  return (
    TRANSITION_BLOCK_MESSAGES[key] ??
    `Cannot move directly from ${from} to ${to}.`
  );
}

export interface ApplicationNote {
  id: string;
  application_id: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface Application {
  id: string;
  job_title: string;
  company: string;
  status: ApplicationStatus;
  fit_score?: number;
  applied_at?: string;
  created_at: string;
  updated_at: string;
  notes_count?: number;
}

export interface ApplicationStatsData {
  by_status: Record<ApplicationStatus, number>;
  avg_days_per_stage: Record<ApplicationStatus, number>;
  total: number;
}
