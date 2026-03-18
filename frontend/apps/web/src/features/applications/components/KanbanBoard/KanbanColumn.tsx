"use client";

// KanbanColumn.tsx — Column component for Kanban board (FE-6.1)

import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Application, ApplicationStatus } from "../../types";
import { KanbanCard, type KanbanCardProps } from "./KanbanCard";

export interface KanbanColumnProps {
  status: ApplicationStatus;
  label: string;
  applications: Application[];
  colorClass: string;
  onCardClick?: KanbanCardProps["onCardClick"];
}

export function KanbanColumn({
  status,
  label,
  applications,
  colorClass,
  onCardClick,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status });

  return (
    <div
      className="flex-shrink-0 w-64 rounded-lg bg-muted/30 p-3 flex flex-col gap-2"
      aria-label={`${label} applications`}
      data-status={status}
      data-testid={`kanban-column-${status.toLowerCase()}`}
    >
      {/* Column header */}
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold text-muted-foreground">{label}</h3>
        <span
          className={`rounded-full px-1.5 py-0.5 text-xs font-medium ${colorClass}`}
          aria-label={`${applications.length} applications`}
        >
          {applications.length}
        </span>
      </div>

      {/* Drop zone */}
      <div
        ref={setNodeRef}
        role="list"
        aria-label={`${label} applications list`}
        className={[
          "flex flex-col gap-2 min-h-[60px] rounded-md transition-colors",
          isOver ? "bg-primary/5 ring-2 ring-primary/30" : "",
        ].join(" ")}
      >
        <SortableContext
          items={applications.map((a) => a.id)}
          strategy={verticalListSortingStrategy}
        >
          {applications.map((app) => (
            <KanbanCard
              key={app.id}
              application={app}
              onCardClick={onCardClick}
            />
          ))}
        </SortableContext>

        {applications.length === 0 && (
          <p className="text-xs text-muted-foreground py-4 text-center">
            No applications
          </p>
        )}
      </div>
    </div>
  );
}
