"use client";

import { QueryClient } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";
import { useState, useMemo } from "react";
import { openDB } from "idb";
import type { IDBPDatabase } from "idb";
import "@/shared/lib/configure-api"; // Wire up 401 auto-refresh interceptor (NFR-R3)

const ONE_HOUR = 60 * 60 * 1000;
const TWENTY_FOUR_HOURS = 24 * ONE_HOUR;

const IDB_NAME = "reqruit-cache";
const IDB_STORE = "query-cache";

/** Lazily opened IndexedDB connection (singleton). */
let dbPromise: Promise<IDBPDatabase> | null = null;

function getDB(): Promise<IDBPDatabase> {
  if (!dbPromise) {
    dbPromise = openDB(IDB_NAME, 1, {
      upgrade(db) {
        if (!db.objectStoreNames.contains(IDB_STORE)) {
          db.createObjectStore(IDB_STORE);
        }
      },
    });
  }
  return dbPromise;
}

/**
 * AsyncStorage adapter backed by IndexedDB via `idb`.
 * Handles larger cache payloads without hitting localStorage's ~5 MB limit.
 * Created lazily to avoid SSR issues (IndexedDB is not available on the server).
 */
function createPersister() {
  return createAsyncStoragePersister({
    storage:
      typeof window !== "undefined"
        ? {
            getItem: async (key: string) => {
              const db = await getDB();
              const value = await db.get(IDB_STORE, key);
              return (value as string) ?? null;
            },
            setItem: async (key: string, value: string) => {
              const db = await getDB();
              await db.put(IDB_STORE, value, key);
            },
            removeItem: async (key: string) => {
              const db = await getDB();
              await db.delete(IDB_STORE, key);
            },
          }
        : undefined,
    key: "reqruit-query-cache",
  });
}

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000, // 1 minute default
            gcTime: TWENTY_FOUR_HOURS, // Keep cached data for 24h for offline persistence
            refetchOnReconnect: true,
            retry: (failureCount, error) => {
              // Don't retry on 4xx errors
              if (error instanceof Error && "status" in error) {
                const status = (error as { status: number }).status;
                if (status >= 400 && status < 500) return false;
              }
              return failureCount < 3;
            },
          },
          mutations: {
            networkMode: "offlineFirst",
          },
        },
      })
  );

  const persister = useMemo(() => createPersister(), []);

  return (
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{
        persister,
        maxAge: TWENTY_FOUR_HOURS,
        buster: "v1", // Bump to invalidate persisted cache after breaking changes
      }}
    >
      {children}
    </PersistQueryClientProvider>
  );
}
