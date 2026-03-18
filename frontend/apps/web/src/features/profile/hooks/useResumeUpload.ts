// useResumeUpload.ts — FE-4.1: Resume upload mutation hook

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient, ApiError, queryKeys } from "@reqruit/api-client";
import type { ResumeUploadResponse } from "../types";

async function uploadResume(file: File): Promise<ResumeUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return apiClient.upload<ResumeUploadResponse>("/resumes/upload", formData);
}

export function useResumeUpload() {
  const queryClient = useQueryClient();

  return useMutation<ResumeUploadResponse, ApiError, File>({
    mutationFn: uploadResume,

    onSuccess: () => {
      // Invalidate resumes list so the parse-status view can load (FE-4.2)
      void queryClient.invalidateQueries({ queryKey: queryKeys.profile.resumes() });
    },

    onError: () => {
      toast.error("Upload failed — please try again");
    },
  });
}
