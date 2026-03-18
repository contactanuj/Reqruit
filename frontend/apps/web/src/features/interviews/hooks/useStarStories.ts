// useStarStories.ts — CRUD hooks for STAR story library (FE-11.1)

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { StarStory, StarStoryFormData } from "../types";

export function useStarStoriesQuery() {
  return useQuery<StarStory[], ApiError>({
    queryKey: queryKeys.interview.starStories(),
    queryFn: () => apiClient.get<StarStory[]>("/interview/star-stories"),
  });
}

export function useCreateStarStory() {
  const queryClient = useQueryClient();

  return useMutation<StarStory, ApiError, StarStoryFormData>({
    mutationFn: (data) =>
      apiClient.post<StarStory>("/interview/star-stories", data),

    onSuccess: (newStory) => {
      queryClient.setQueryData<StarStory[]>(
        queryKeys.interview.starStories(),
        (old) => (old ? [...old, newStory] : [newStory]),
      );
      toast.success("STAR story created");
    },

    onError: () => {
      toast.error("Failed to create STAR story — please try again");
    },
  });
}

export function useUpdateStarStory() {
  const queryClient = useQueryClient();

  return useMutation<StarStory, ApiError, { id: string; data: StarStoryFormData }>({
    mutationFn: ({ id, data }) =>
      apiClient.patch<StarStory>(`/interview/star-stories/${id}`, data),

    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.interview.starStories() });
      const previous = queryClient.getQueryData<StarStory[]>(
        queryKeys.interview.starStories(),
      );
      queryClient.setQueryData<StarStory[]>(
        queryKeys.interview.starStories(),
        (old) =>
          old?.map((s) =>
            s.id === id ? { ...s, ...data, updated_at: new Date().toISOString() } : s,
          ),
      );
      return { previous };
    },

    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.interview.starStories(), context.previous);
      }
      toast.error("Failed to update STAR story — please try again");
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.interview.starStories() });
    },
  });
}

export function useDeleteStarStory() {
  const queryClient = useQueryClient();

  return useMutation<void, ApiError, string>({
    mutationFn: (id) =>
      apiClient.delete<void>(`/interview/star-stories/${id}`),

    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.interview.starStories() });
      const previous = queryClient.getQueryData<StarStory[]>(
        queryKeys.interview.starStories(),
      );
      queryClient.setQueryData<StarStory[]>(
        queryKeys.interview.starStories(),
        (old) => old?.filter((s) => s.id !== id),
      );
      return { previous };
    },

    onError: (_err, _id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.interview.starStories(), context.previous);
      }
      toast.error("Failed to delete STAR story — please try again");
    },

    onSuccess: () => {
      toast.success("STAR story deleted");
    },

    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.interview.starStories() });
    },
  });
}
