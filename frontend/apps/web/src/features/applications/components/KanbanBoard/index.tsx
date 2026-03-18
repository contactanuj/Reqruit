"use client";

// KanbanBoard/index.tsx — Seven-column dnd-kit Kanban board (FE-6.1, FE-6.2)

import { useState, useEffect, useRef, useCallback } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import type { Application, ApplicationStatus } from "../../types";
import { KANBAN_COLUMNS } from "../../types";
import { guardStatusTransition } from "../StatusTransitionGuard";
import { KanbanColumn } from "./KanbanColumn";
import { KanbanCard } from "./KanbanCard";
import { useOptimisticStatusMove } from "../../hooks/useOptimisticStatusMove";

export interface KanbanBoardProps {
  applications: Application[];
  isPending?: boolean;
  onCardClick?: (application: Application) => void;
}

export function KanbanBoard({ applications, isPending, onCardClick }: KanbanBoardProps) {
  const [activeApplication, setActiveApplication] = useState<Application | null>(null);
  const [activeColumnIndex, setActiveColumnIndex] = useState(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const statusMove = useOptimisticStatusMove();

  // Track active column via IntersectionObserver for mobile dot indicators
  const observerRef = useRef<IntersectionObserver | null>(null);
  const columnRefsCallback = useCallback((node: HTMLDivElement | null, index: number) => {
    if (!node) return;
    node.setAttribute("data-column-index", String(index));
  }, []);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const idx = Number((entry.target as HTMLElement).dataset.columnIndex);
            if (!Number.isNaN(idx)) setActiveColumnIndex(idx);
          }
        }
      },
      { root: container, threshold: 0.6 }
    );

    const columns = container.querySelectorAll<HTMLElement>("[data-column-index]");
    columns.forEach((col) => observerRef.current!.observe(col));

    return () => observerRef.current?.disconnect();
  }, [isPending, applications]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5, // Only start drag after 5px movement (prevents accidental drags)
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Group applications by status
  const grouped = KANBAN_COLUMNS.reduce<Record<ApplicationStatus, Application[]>>(
    (acc, col) => {
      acc[col.status] = applications.filter((a) => a.status === col.status);
      return acc;
    },
    {} as Record<ApplicationStatus, Application[]>
  );

  function handleDragStart(event: DragStartEvent) {
    const app = applications.find((a) => a.id === event.active.id);
    setActiveApplication(app ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveApplication(null);

    if (!over) return;

    const draggedApp = applications.find((a) => a.id === active.id);
    if (!draggedApp) return;

    // Determine target column — over.id can be a column status or a card id
    let targetStatus = over.id as ApplicationStatus;

    // If dropped over a card rather than the column droppable, find the card's column
    const overApp = applications.find((a) => a.id === over.id);
    if (overApp) {
      targetStatus = overApp.status;
    }

    // Same column — no action needed
    if (draggedApp.status === targetStatus) return;

    // Validate transition via shared guard (FE-6.2)
    if (!guardStatusTransition(draggedApp.status, targetStatus)) return;

    // Fire optimistic update (FE-6.1, AC#2)
    statusMove.mutate({
      applicationId: draggedApp.id,
      newStatus: targetStatus,
      previousStatus: draggedApp.status,
    });
  }

  if (isPending) {
    return (
      <div
        className="flex gap-4 overflow-x-auto pb-4"
        aria-label="Loading kanban board"
        data-testid="kanban-board-loading"
      >
        {KANBAN_COLUMNS.map((col) => (
          <div
            key={col.status}
            className="flex-shrink-0 w-64 rounded-lg bg-muted/30 p-3"
          >
            <h3 className="text-sm font-semibold mb-3 text-muted-foreground">
              {col.label}
            </h3>
            {/* 2 skeleton cards per column while loading */}
            {[1, 2].map((i) => (
              <div
                key={i}
                aria-hidden="true"
                className="rounded-lg border border-border bg-card p-3 mb-2 animate-pulse"
                data-testid="skeleton-kanban-card"
              >
                <div className="h-3 w-20 rounded bg-muted mb-1" />
                <div className="h-4 w-36 rounded bg-muted mb-2" />
                <div className="h-5 w-16 rounded-full bg-muted" />
              </div>
            ))}
          </div>
        ))}
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div
        ref={scrollContainerRef}
        className="flex gap-4 overflow-x-auto pb-4 snap-x snap-mandatory md:snap-none"
        aria-label="Application tracking kanban board"
        data-testid="kanban-board"
      >
        {KANBAN_COLUMNS.map((col, index) => (
          <div
            key={col.status}
            ref={(node) => columnRefsCallback(node, index)}
            data-column-index={index}
            className="snap-start snap-always min-w-[85vw] md:min-w-0 md:snap-align-none"
          >
            <KanbanColumn
              status={col.status}
              label={col.label}
              colorClass={col.color}
              applications={grouped[col.status]}
              onCardClick={onCardClick}
            />
          </div>
        ))}
      </div>

      {/* Mobile column indicator dots */}
      <div
        className="flex justify-center gap-1.5 pt-2 md:hidden"
        aria-label={`Column ${activeColumnIndex + 1} of ${KANBAN_COLUMNS.length}`}
        data-testid="kanban-column-dots"
      >
        {KANBAN_COLUMNS.map((col, index) => (
          <span
            key={col.status}
            className={[
              "h-2 w-2 rounded-full transition-colors",
              index === activeColumnIndex ? "bg-primary" : "bg-muted-foreground/30",
            ].join(" ")}
            aria-hidden="true"
          />
        ))}
      </div>

      {/* Drag overlay — renders dragged card at cursor position */}
      <DragOverlay>
        {activeApplication ? (
          <KanbanCard application={activeApplication} />
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
