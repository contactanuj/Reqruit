"use client";

// KanbanCard.tsx — Draggable application card for Kanban board (FE-6.1, FE-6.4)

import React from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Application } from "../../types";
import { KANBAN_COLUMNS } from "../../types";
import { useApplicationsStore } from "../../store/applications-store";

export interface KanbanCardProps {
  application: Application;
  onCardClick?: (application: Application) => void;
}

export function KanbanCard({ application, onCardClick }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: application.id });

  const { isSelected, toggleSelect, selectedIds } = useApplicationsStore();
  const isBulkMode = selectedIds.size > 0;
  const selected = isSelected(application.id);

  const statusDef = KANBAN_COLUMNS.find((c) => c.status === application.status);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      data-testid="kanban-card"
      aria-grabbed={isDragging}
      className={[
        "group relative rounded-lg border bg-card p-3 cursor-grab active:cursor-grabbing",
        "hover:border-primary/50 hover:shadow-sm transition-all duration-150",
        "focus-within:ring-2 focus-within:ring-primary",
        isDragging ? "shadow-lg ring-2 ring-primary" : "",
        selected ? "ring-2 ring-primary bg-primary/5" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      {...attributes}
      {...listeners}
      role="listitem"
    >
      {/* Checkbox for bulk operations */}
      <div
        className={[
          "absolute top-2 left-2 transition-opacity",
          isBulkMode ? "opacity-100" : "opacity-0 group-hover:opacity-100 focus-within:opacity-100",
        ].join(" ")}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === " ") {
            e.preventDefault();
            e.stopPropagation();
            toggleSelect(application.id);
          }
        }}
      >
        <input
          type="checkbox"
          aria-label={`Select ${application.company} - ${application.job_title}`}
          aria-checked={selected}
          checked={selected}
          onChange={() => toggleSelect(application.id)}
          className="h-4 w-4 rounded border-border cursor-pointer"
          tabIndex={0}
          onClick={(e) => e.stopPropagation()}
        />
      </div>

      {/* Content */}
      <div
        className={isBulkMode ? "pl-6" : ""}
        onClick={() => onCardClick?.(application)}
        role="button"
        tabIndex={-1}
        aria-label={`${application.job_title} at ${application.company}`}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            onCardClick?.(application);
          }
        }}
      >
        {/* Company */}
        <p className="text-xs font-medium text-muted-foreground truncate mb-0.5">
          {application.company}
        </p>

        {/* Job title */}
        <h4 className="text-sm font-semibold leading-tight mb-1.5 truncate">
          {application.job_title}
        </h4>

        {/* Status badge (icon + text + colour — never colour alone, UX-8) */}
        <div className="flex items-center justify-between gap-1">
          {statusDef && (
            <span
              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusDef.color}`}
              aria-label={`Status: ${statusDef.label}`}
            >
              {statusDef.label}
            </span>
          )}
          {application.fit_score != null && (
            <span
              className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary"
              aria-label={`Fit score: ${application.fit_score}%`}
            >
              {application.fit_score}%
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
