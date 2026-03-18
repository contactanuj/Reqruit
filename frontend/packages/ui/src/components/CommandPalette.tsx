"use client";

// CommandPalette.tsx — Cmd/Ctrl+K command palette (FE-2.3)
// Simple modal with fuzzy search over navigation items and AI actions.
// No cmdk dependency — built from scratch to avoid external dep in packages/ui.

import {
  useState,
  useEffect,
  useCallback,
  useMemo,
} from "react";
import { X, Search } from "lucide-react";
import { useFocusTrap } from "../hooks/use-focus-trap";

export interface CommandItem {
  id: string;
  label: string;
  category: "navigation" | "recent" | "ai-action";
  action: () => void;
}

export interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  items: CommandItem[];
  /** Optional callback invoked when a command is selected. If provided, replaces the default action()+onClose() behaviour. */
  onSelect?: (item: CommandItem) => void;
}

/** Simple case-insensitive substring + word-start fuzzy filter */
function filterItems(items: CommandItem[], query: string): CommandItem[] {
  if (!query.trim()) return items;
  const q = query.toLowerCase();
  return items.filter((item) => item.label.toLowerCase().includes(q));
}

const CATEGORY_LABELS: Record<CommandItem["category"], string> = {
  navigation: "Navigation",
  recent: "Recent",
  "ai-action": "AI Actions",
};

export function CommandPalette({ open, onClose, items, onSelect }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const { dialogRef, handleBackdropClick } = useFocusTrap({ open, onClose });
  const inputRef = useCallback((node: HTMLInputElement | null) => {
    if (node && open) node.focus();
  }, [open]);

  // Reset state on close
  useEffect(() => {
    if (!open) {
      setQuery("");
      setSelectedIndex(0);
    }
  }, [open]);

  const filtered = useMemo(() => filterItems(items, query), [items, query]);

  // Group by category
  const grouped = useMemo(() => {
    const map = new Map<CommandItem["category"], CommandItem[]>();
    for (const item of filtered) {
      const list = map.get(item.category) ?? [];
      list.push(item);
      map.set(item.category, list);
    }
    return map;
  }, [filtered]);

  // Flat list for keyboard navigation
  const flatList = useMemo(
    () => Array.from(grouped.values()).flat(),
    [grouped],
  );

  const handleSelect = useCallback(
    (item: CommandItem) => {
      if (onSelect) {
        onSelect(item);
      } else {
        item.action();
        onClose();
      }
    },
    [onClose, onSelect],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, flatList.length - 1));
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        const item = flatList[selectedIndex];
        if (item) handleSelect(item);
      }
    },
    [flatList, selectedIndex, handleSelect],
  );

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Pre-compute flat index map for selection tracking
  const flatIndexMap = useMemo(() => {
    const map = new Map<string, number>();
    let idx = 0;
    for (const [, categoryItems] of grouped.entries()) {
      for (const item of categoryItems) {
        map.set(item.id, idx++);
      }
    }
    return map;
  }, [grouped]);

  if (!open) return null;

  return (
    /* Backdrop */
    <div
      role="presentation"
      className="fixed inset-0 z-50 flex items-start justify-center pt-[10vh] bg-black/50 backdrop-blur-sm md:pt-[15vh] max-md:pt-0"
      onClick={handleBackdropClick}
    >
      {/* Dialog */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-label="Command palette"
        aria-modal="true"
        className="relative w-full max-w-lg bg-popover border border-border rounded-lg shadow-2xl overflow-hidden mx-4 md:mx-0 md:max-w-lg max-h-[80vh] md:max-h-[60vh] max-md:fixed max-md:inset-0 max-md:max-w-none max-md:max-h-none max-md:rounded-none max-md:mx-0 max-md:border-0 flex flex-col"
        onKeyDown={handleKeyDown}
      >
        {/* Search input */}
        <div className="flex items-center border-b border-border px-3 gap-2">
          <Search className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden="true" />
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-label="Search commands"
            aria-expanded={true}
            aria-autocomplete="list"
            aria-activedescendant={
              flatList[selectedIndex]
                ? `cmd-item-${flatList[selectedIndex].id}`
                : undefined
            }
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search commands, pages, AI actions…"
            className="flex-1 bg-transparent py-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
          <button
            type="button"
            onClick={onClose}
            aria-label="Close command palette"
            className="p-1 rounded text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {/* Results */}
        <div
          role="listbox"
          aria-label="Search results"
          className="overflow-y-auto flex-1"
        >
          {filtered.length === 0 ? (
            <p className="text-center text-muted-foreground text-sm py-8">
              No results for &quot;{query}&quot;
            </p>
          ) : (
            Array.from(grouped.entries()).map(([category, categoryItems]) => (
              <div key={category}>
                <div className="px-3 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider bg-muted/50">
                  {CATEGORY_LABELS[category]}
                </div>
                {categoryItems.map((item) => {
                  const idx = flatIndexMap.get(item.id) ?? -1;
                  const isSelected = idx === selectedIndex;
                  return (
                    <button
                      key={item.id}
                      id={`cmd-item-${item.id}`}
                      type="button"
                      role="option"
                      aria-selected={isSelected}
                      onClick={() => handleSelect(item)}
                      className={[
                        "w-full text-start px-3 py-2.5 text-sm transition-colors",
                        isSelected
                          ? "bg-accent text-accent-foreground"
                          : "text-foreground hover:bg-accent/50",
                      ].join(" ")}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
