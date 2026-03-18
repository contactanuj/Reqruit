// useDiscoverySources.ts — Admin discovery source hooks (FE-15.2)

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { DiscoverySource } from "../types";

// ---------------------------------------------------------------------------
// useDiscoverySourcesQuery — FE-15.2: GET /admin/discovery/sources
// ---------------------------------------------------------------------------

export function useDiscoverySourcesQuery() {
  return useQuery<DiscoverySource[], ApiError>({
    queryKey: queryKeys.admin.discoverySources(),
    queryFn: () => apiClient.get<DiscoverySource[]>("/admin/discovery/sources"),
    staleTime: 60 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useSyncSource — FE-15.2: POST /admin/discovery/sources/{id}/sync
// ---------------------------------------------------------------------------

export function useSyncSource() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, { id: string }>({
    mutationFn: ({ id }) =>
      apiClient.post<void>(`/admin/discovery/sources/${id}/sync`, {}),

    onSuccess: () => {
      toast.success("Sync triggered", { duration: 3000 });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.admin.discoverySources(),
      });
    },

    onError: () => {
      toast.error("Sync failed — please try again");
    },
  });
}
