"use client";

// LocaleConfigTable.tsx — FE-15.1: Inline-editable locale configuration table

import { useState, useCallback } from "react";
import { useLocaleConfigQuery, useUpdateLocaleConfig } from "../hooks/useLocaleConfig";
import type { LocaleConfig } from "../types";

export function LocaleConfigTable() {
  const { data: configs, isLoading, isError } = useLocaleConfigQuery();
  const updateMutation = useUpdateLocaleConfig();

  const [editingLocale, setEditingLocale] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<Partial<LocaleConfig>>({});

  const startEdit = useCallback((config: LocaleConfig) => {
    setEditingLocale(config.locale);
    setEditValues({
      currencySymbol: config.currencySymbol,
      salaryRangeMin: config.salaryRangeMin,
      salaryRangeMax: config.salaryRangeMax,
      noticePeriodDefault: config.noticePeriodDefault,
      jobBoardSources: config.jobBoardSources,
    });
  }, []);

  const cancelEdit = useCallback(() => {
    setEditingLocale(null);
    setEditValues({});
  }, []);

  const saveEdit = useCallback(() => {
    if (!editingLocale) return;
    updateMutation.mutate(
      { locale: editingLocale, data: editValues },
      {
        onSuccess: () => {
          setEditingLocale(null);
          setEditValues({});
        },
      },
    );
  }, [editingLocale, editValues, updateMutation]);

  if (isLoading) {
    return (
      <div data-testid="locale-config-skeleton" className="animate-pulse space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 rounded bg-gray-200" />
        ))}
      </div>
    );
  }

  if (isError) {
    return (
      <div data-testid="locale-config-error" className="rounded border border-red-300 bg-red-50 p-4 text-red-700">
        Failed to load locale configuration.
      </div>
    );
  }

  return (
    <div data-testid="locale-config-table" className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Locale</th>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Currency</th>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Salary Min</th>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Salary Max</th>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Notice Period (days)</th>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Job Board Sources</th>
            <th className="px-4 py-2 text-left text-sm font-medium text-gray-600">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {configs?.map((config) => {
            const isEditing = editingLocale === config.locale;
            return (
              <tr key={config.locale} data-testid={`locale-row-${config.locale}`}>
                <td className="px-4 py-2 text-sm font-medium">{config.locale}</td>

                {isEditing ? (
                  <>
                    <td className="px-4 py-2">
                      <input
                        data-testid={`edit-currency-${config.locale}`}
                        className="w-16 rounded border px-2 py-1 text-sm"
                        value={editValues.currencySymbol ?? ""}
                        onChange={(e) =>
                          setEditValues((v) => ({ ...v, currencySymbol: e.target.value }))
                        }
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        data-testid={`edit-salary-min-${config.locale}`}
                        type="number"
                        className="w-24 rounded border px-2 py-1 text-sm"
                        value={editValues.salaryRangeMin ?? 0}
                        onChange={(e) =>
                          setEditValues((v) => ({ ...v, salaryRangeMin: Number(e.target.value) }))
                        }
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        data-testid={`edit-salary-max-${config.locale}`}
                        type="number"
                        className="w-24 rounded border px-2 py-1 text-sm"
                        value={editValues.salaryRangeMax ?? 0}
                        onChange={(e) =>
                          setEditValues((v) => ({ ...v, salaryRangeMax: Number(e.target.value) }))
                        }
                      />
                    </td>
                    <td className="px-4 py-2">
                      <input
                        data-testid={`edit-notice-${config.locale}`}
                        type="number"
                        className="w-20 rounded border px-2 py-1 text-sm"
                        value={editValues.noticePeriodDefault ?? 0}
                        onChange={(e) =>
                          setEditValues((v) => ({
                            ...v,
                            noticePeriodDefault: Number(e.target.value),
                          }))
                        }
                      />
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-600">
                      {config.jobBoardSources.join(", ")}
                    </td>
                    <td className="flex gap-2 px-4 py-2">
                      <button
                        data-testid={`save-button-${config.locale}`}
                        onClick={saveEdit}
                        disabled={updateMutation.isPending}
                        className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                      >
                        {updateMutation.isPending ? "Saving..." : "Save"}
                      </button>
                      <button
                        data-testid={`cancel-button-${config.locale}`}
                        onClick={cancelEdit}
                        disabled={updateMutation.isPending}
                        className="rounded border px-3 py-1 text-sm hover:bg-gray-100 disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-4 py-2 text-sm">{config.currencySymbol}</td>
                    <td className="px-4 py-2 text-sm">{config.salaryRangeMin.toLocaleString()}</td>
                    <td className="px-4 py-2 text-sm">{config.salaryRangeMax.toLocaleString()}</td>
                    <td className="px-4 py-2 text-sm">{config.noticePeriodDefault}</td>
                    <td className="px-4 py-2 text-sm text-gray-600">
                      {config.jobBoardSources.join(", ")}
                    </td>
                    <td className="px-4 py-2">
                      <button
                        data-testid={`edit-button-${config.locale}`}
                        onClick={() => startEdit(config)}
                        disabled={editingLocale !== null}
                        className="rounded border px-3 py-1 text-sm hover:bg-gray-100 disabled:opacity-50"
                      >
                        Edit
                      </button>
                    </td>
                  </>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
