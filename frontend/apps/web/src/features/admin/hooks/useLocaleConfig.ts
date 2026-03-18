// useLocaleConfig.ts — Admin locale config hooks (FE-15.1)

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { LocaleConfig } from "../types";

// ---------------------------------------------------------------------------
// useLocaleConfigQuery — FE-15.1: GET /admin/locale-config
// ---------------------------------------------------------------------------

export function useLocaleConfigQuery() {
  return useQuery<LocaleConfig[], ApiError>({
    queryKey: queryKeys.admin.localeConfig(),
    queryFn: () => apiClient.get<LocaleConfig[]>("/admin/locale-config"),
    staleTime: 5 * 60 * 1000,
  });
}

// ---------------------------------------------------------------------------
// useUpdateLocaleConfig — FE-15.1: PATCH /admin/locale-config/{locale}
// ---------------------------------------------------------------------------

export function useUpdateLocaleConfig() {
  const queryClient = useQueryClient();

  return useMutation<LocaleConfig, ApiError, { locale: string; data: Partial<LocaleConfig> }>({
    mutationFn: ({ locale, data }) =>
      apiClient.patch<LocaleConfig>(`/admin/locale-config/${locale}`, data),

    onMutate: async ({ locale, data }) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.admin.localeConfig(),
      });

      const previous = queryClient.getQueryData<LocaleConfig[]>(
        queryKeys.admin.localeConfig(),
      );

      if (previous) {
        queryClient.setQueryData<LocaleConfig[]>(
          queryKeys.admin.localeConfig(),
          previous.map((config) =>
            config.locale === locale ? { ...config, ...data } : config,
          ),
        );
      }

      return { previous };
    },

    onError: (_error, _payload, context) => {
      const ctx = context as { previous?: LocaleConfig[] } | undefined;
      if (ctx?.previous) {
        queryClient.setQueryData<LocaleConfig[]>(
          queryKeys.admin.localeConfig(),
          ctx.previous,
        );
      }
      toast.error("Failed to update locale config — please try again");
    },

    onSuccess: () => {
      toast.success("Locale config updated", { duration: 3000 });
    },

    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.admin.localeConfig(),
      });
    },
  });
}
