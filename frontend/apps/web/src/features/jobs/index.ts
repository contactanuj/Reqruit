// Jobs feature public API (FE-5)

export { useJobShortlist, useSavedJobs } from "./hooks/useJobList";
export { useParseJobUrl, useAddJob } from "./hooks/useAddJob";
export {
  useCompanyResearch,
  useGenerateCompanyResearch,
  useJobContacts,
  useAddContact,
  useDeleteContact,
} from "./hooks/useJobDetail";
export { useJobsStore } from "./store/jobs-store";
export type { JobsViewMode } from "./store/jobs-store";
export type {
  JobListing,
  SavedJob,
  JobStatus,
  Contact,
  CompanyResearch,
  JobFilters,
  AddJobPayload,
  AddContactPayload,
  RemotePreference,
  ContactRoleType,
} from "./types";
