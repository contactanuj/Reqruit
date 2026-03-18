// useOfflineSync.ts — Offline write queue monitoring (FE-9.3)
// Works with TanStack Query's networkMode: 'offlineFirst' to track and sync queued mutations.

import { useState, useEffect, useCallback, useRef } from "react";
import { useQueryClient, useMutationState } from "@tanstack/react-query";
import { toast } from "sonner";

export interface OfflineSyncHook {
  /** Number of mutations currently paused / queued offline */
  pendingCount: number;
  /** Whether any mutations are queued for sync */
  hasPendingMutations: boolean;
  /** Whether the device is currently online */
  isOnline: boolean;
  /** Check if a specific query key has a pending (paused) mutation — useful for per-item sync badges */
  hasPendingMutationFor: (queryKey: readonly unknown[]) => boolean;
}

export function useOfflineSync(): OfflineSyncHook {
  const queryClient = useQueryClient();
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true
  );
  const isSyncingRef = useRef(false);

  // Get all paused (offline-queued) mutations
  const pausedMutations = useMutationState({
    filters: { status: "pending" },
    select: (mutation) => mutation.state,
  });

  const pendingCount = pausedMutations.filter(
    (state) => state.isPaused
  ).length;

  const hasPendingMutations = pendingCount > 0;

  const retrySyncMutations = useCallback(() => {
    if (isSyncingRef.current) return;
    isSyncingRef.current = true;

    const mutationCache = queryClient.getMutationCache();
    let successCount = 0;
    let errorCount = 0;
    const totalPaused = mutationCache.getAll().filter(
      (m) => m.state.isPaused
    ).length;

    if (totalPaused === 0) {
      isSyncingRef.current = false;
      return;
    }

    // Subscribe to mutation cache events to detect completion
    const unsubscribe = mutationCache.subscribe((event) => {
      if (event.type === "updated") {
        const state = event.mutation.state;
        if (state.status === "success") {
          successCount++;
        } else if (state.status === "error") {
          errorCount++;
        }

        // Check if all paused mutations have resolved
        if (successCount + errorCount >= totalPaused) {
          unsubscribe();
          isSyncingRef.current = false;

          if (errorCount > 0) {
            toast.error("Sync failed — tap to retry", {
              duration: 0,
              action: {
                label: "Retry",
                onClick: () => retrySyncMutations(),
              },
            });
          } else {
            toast.info("Synced", { duration: 2000 });
          }
        }
      }
    });

    // Resume paused mutations
    queryClient.resumePausedMutations().catch(() => {
      unsubscribe();
      isSyncingRef.current = false;
      toast.error("Sync failed — tap to retry", {
        duration: 0,
        action: {
          label: "Retry",
          onClick: () => retrySyncMutations(),
        },
      });
    });
  }, [queryClient]);

  const handleOnline = useCallback(() => {
    setIsOnline(true);
  }, []);

  const handleOffline = useCallback(() => {
    setIsOnline(false);
  }, []);

  useEffect(() => {
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [handleOnline, handleOffline]);

  // When coming back online with pending mutations, trigger sync
  useEffect(() => {
    if (isOnline && hasPendingMutations) {
      retrySyncMutations();
    }
  }, [isOnline, hasPendingMutations, retrySyncMutations]);

  /**
   * Check whether a specific query key has any paused mutations.
   * Consumers can use this to show per-item sync badges, e.g.:
   *   const hasPending = hasPendingMutationFor(queryKeys.applications.detail(id));
   */
  const hasPendingMutationFor = useCallback(
    (queryKey: readonly unknown[]): boolean => {
      const mutationCache = queryClient.getMutationCache();
      return mutationCache.getAll().some((mutation) => {
        if (!mutation.state.isPaused) return false;
        const mutationKey = mutation.options.mutationKey;
        if (!mutationKey) return false;
        // Prefix match: check if the mutation key starts with all elements of the query key
        return queryKey.every((segment, i) => mutationKey[i] === segment);
      });
    },
    [queryClient]
  );

  return {
    pendingCount,
    hasPendingMutations,
    isOnline,
    hasPendingMutationFor,
  };
}
