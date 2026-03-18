// Profile feature types (FE-4)

export interface WorkExperience {
  id: string;
  title: string;
  company: string;
  location?: string;
  startDate: string; // ISO date string — format at render time (Rule 10)
  endDate?: string | null; // null means "present"
  description?: string;
}

export interface Education {
  id: string;
  degree: string;
  institution: string;
  field?: string;
  startDate: string;
  endDate?: string | null;
  grade?: string;
}

export type SkillCategory = "Technical" | "Soft" | "Tools";

export interface Skill {
  id: string;
  name: string;
  category: SkillCategory;
  proficiency?: number; // 0–100
}

export interface ContactInfo {
  name: string;
  email: string;
  phone?: string;
  location?: string;
}

export interface Profile {
  id: string;
  contact: ContactInfo;
  headline?: string;
  summary?: string;
  experience: WorkExperience[];
  education: Education[];
  skills: Skill[];
  targetRoles: string[];
  targetCompanies: string[];
  remotePreference?: "Remote" | "Hybrid" | "On-site";
  salaryRange?: { min: number; max: number };
  noticePeriod?: number; // days
  visaRequirement?: string;
}

export type ResumeParseStatus = "pending" | "processing" | "completed" | "failed";

export interface ResumeVersion {
  id: string;
  filename: string;
  uploadedAt: string; // ISO date — format at render time (Rule 10)
  parseStatus: ResumeParseStatus;
  isMaster: boolean;
}

export interface ResumeUploadResponse {
  id: string;
  filename: string;
  parseStatus: ResumeParseStatus;
}

export interface ResumeStatusResponse {
  id: string;
  status: ResumeParseStatus;
  message?: string;
}

export interface SkillWithProficiency {
  name: string;
  category: SkillCategory;
  proficiency: number; // 0–100
}

export interface TrendingSkill {
  name: string;
  demand: "high" | "medium" | "low";
}

export interface SkillGap {
  name: string;
  exampleJD?: string;
  learningResource?: string;
}

export interface SkillAnalysis {
  yourSkills: SkillWithProficiency[];
  trendingInTargetRoles: TrendingSkill[];
  skillGaps: SkillGap[];
  generatedAt: string;
}

export interface UpdateProfilePayload {
  headline?: string;
  summary?: string;
  targetRoles?: string[];
  targetCompanies?: string[];
  remotePreference?: "Remote" | "Hybrid" | "On-site";
  location?: string;
  salaryRange?: { min: number; max: number };
  noticePeriod?: number;
  visaRequirement?: string;
}
