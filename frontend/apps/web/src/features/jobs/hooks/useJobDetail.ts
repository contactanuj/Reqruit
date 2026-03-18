// useJobDetail.ts — Job detail hooks (FE-5.5, FE-5.7)

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { CompanyResearch, Contact, AddContactPayload } from "../types";

// ---------------------------------------------------------------------------
// useCompanyResearch — FE-5.5: GET /jobs/{id}/company-research
// ---------------------------------------------------------------------------

export function useCompanyResearch(jobId: string) {
  return useQuery<CompanyResearch | null, ApiError>({
    queryKey: queryKeys.jobs.companyResearch(jobId),
    queryFn: async () => {
      try {
        return await apiClient.get<CompanyResearch>(`/jobs/${jobId}/company-research`);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
    staleTime: 60 * 60 * 1000, // 1 hour (company research doesn't change often)
    enabled: !!jobId,
  });
}

// ---------------------------------------------------------------------------
// useGenerateCompanyResearch — FE-5.5: POST /jobs/{id}/company-research
// ---------------------------------------------------------------------------

export function useGenerateCompanyResearch(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation<CompanyResearch, ApiError, void>({
    mutationFn: () =>
      apiClient.post<CompanyResearch>(`/jobs/${jobId}/company-research`, {}),

    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.jobs.companyResearch(jobId),
      });
    },
  });
}

// ---------------------------------------------------------------------------
// useJobContacts — FE-5.7: GET /jobs/{id}/contacts
// ---------------------------------------------------------------------------

export function useJobContacts(jobId: string) {
  return useQuery<Contact[], ApiError>({
    queryKey: queryKeys.jobs.contacts(jobId),
    queryFn: () => apiClient.get<Contact[]>(`/jobs/${jobId}/contacts`),
    enabled: !!jobId,
  });
}

// ---------------------------------------------------------------------------
// useAddContact — FE-5.7: POST /jobs/{id}/contacts
// ---------------------------------------------------------------------------

export function useAddContact(jobId: string, onSuccess?: () => void) {
  const queryClient = useQueryClient();

  return useMutation<Contact, ApiError, AddContactPayload>({
    mutationFn: (payload) =>
      apiClient.post<Contact>(`/jobs/${jobId}/contacts`, payload),

    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.jobs.contacts(jobId) });
      const previous = queryClient.getQueryData<Contact[]>(queryKeys.jobs.contacts(jobId));

      // Optimistic: add to list immediately
      if (previous) {
        const optimistic: Contact = {
          id: `optimistic-${Date.now()}`,
          name: payload.name,
          role_type: payload.role_type,
          linkedin_url: payload.linkedin_url,
          email: payload.email,
        };
        queryClient.setQueryData<Contact[]>(queryKeys.jobs.contacts(jobId), [
          ...previous,
          optimistic,
        ]);
      }

      return { previous };
    },

    onError: (_error, _payload, context) => {
      const ctx = context as { previous?: Contact[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<Contact[]>(queryKeys.jobs.contacts(jobId), ctx.previous);
      }
    },

    onSuccess: () => {
      onSuccess?.();
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.contacts(jobId) });
    },
  });
}

// ---------------------------------------------------------------------------
// useDeleteContact — FE-5.7: DELETE /jobs/{id}/contacts/{contact_id}
// ---------------------------------------------------------------------------

export function useDeleteContact(jobId: string) {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, string>({
    mutationFn: (contactId) =>
      apiClient.delete<void>(`/jobs/${jobId}/contacts/${contactId}`),

    onMutate: async (contactId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.jobs.contacts(jobId) });
      const previous = queryClient.getQueryData<Contact[]>(queryKeys.jobs.contacts(jobId));

      // Optimistic: remove from list immediately
      if (previous) {
        queryClient.setQueryData<Contact[]>(
          queryKeys.jobs.contacts(jobId),
          previous.filter((c) => c.id !== contactId)
        );
      }

      return { previous };
    },

    onError: (_error, _contactId, context) => {
      const ctx = context as { previous?: Contact[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<Contact[]>(queryKeys.jobs.contacts(jobId), ctx.previous);
      }
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.jobs.contacts(jobId) });
    },
  });
}
