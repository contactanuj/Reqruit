// Job feature types (FE-5)

export type JobStatus =
  | "saved"
  | "applied"
  | "phone_screen"
  | "interview"
  | "offer"
  | "rejected"
  | "withdrawn";

export type RemotePreference = "Remote" | "Hybrid" | "On-site";

export type ContactRoleType = "Recruiter" | "Engineer" | "Hiring Manager" | "Generic";

export interface JobListing {
  id: string;
  title: string;
  company: string;
  location: string;
  remote_preference?: RemotePreference;
  salary_min?: number; // raw number — format at render time (Rule 10)
  salary_max?: number;
  description?: string;
  url?: string;
  fit_score?: number; // 0–100
  roi_prediction?: string; // e.g. "High ROI" label
  staleness_score?: number; // days since last activity
  posted_at?: string; // ISO date
  last_verified_at?: string; // ISO date
  created_at: string; // ISO date — format at render time
  status: JobStatus;
  locale?: "IN" | "US";
  is_new?: boolean; // true if returned in a background refetch
}

export type SavedJob = JobListing;

export interface Contact {
  id: string;
  name: string;
  role_type: ContactRoleType;
  linkedin_url?: string;
  email?: string;
}

export interface CompanyResearch {
  culture_summary?: string;
  tech_stack?: string[];
  glassdoor_rating?: number; // 0–5
  interview_patterns?: InterviewPattern[];
  generated_at?: string; // ISO date
}

export interface InterviewPattern {
  theme: string;
  description?: string;
}

export interface AddJobPayload {
  title: string;
  company: string;
  location?: string;
  remote_preference?: RemotePreference;
  salary_min?: number;
  salary_max?: number;
  description?: string;
  url?: string;
}

export interface ParseJobUrlPayload {
  url: string;
}

export interface ParseJobUrlResult {
  title?: string;
  company?: string;
  location?: string;
  description?: string;
}

export interface AddContactPayload {
  name: string;
  role_type: ContactRoleType;
  linkedin_url?: string;
  email?: string;
}

export interface JobFilters {
  q?: string;
  status?: JobStatus[];
  remote?: RemotePreference[];
  salary_min?: number;
  salary_max?: number;
  date_from?: string;
  date_to?: string;
}
