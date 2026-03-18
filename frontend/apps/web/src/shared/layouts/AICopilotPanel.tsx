"use client";

// AICopilotPanel.tsx — Context-aware AI Copilot panel (FE-2.6)

import { useState, useRef, useEffect } from "react";
import { X, Send } from "lucide-react";
import { apiClient } from "@reqruit/api-client";
import { useLayoutStore } from "@/features/shell/store/layout-store";
import { cn } from "@/lib/utils";
import { useCopilotContext } from "@/features/shell/hooks/use-copilot-context";
import { useSSEStream } from "@repo/ui/hooks";
import { useStreamStore } from "@/features/applications/store/stream-store";

const generateId = (): string =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export function AICopilotPanel() {
  const { copilotVisible, toggleCopilot, setCopilotVisible } = useLayoutStore();
  const { persona, prePrompt, route } = useCopilotContext();

  const appendToken = useStreamStore((s) => s.appendToken);
  const setActiveThread = useStreamStore((s) => s.setActiveThread);
  const resetStream = useStreamStore((s) => s.reset);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streamUrl, setStreamUrl] = useState("");
  const [streamEnabled, setStreamEnabled] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const lastSyncedTextRef = useRef("");

  const { state: sseState, cancel: sseCancel } = useSSEStream({
    url: streamUrl,
    enabled: streamEnabled,
    onComplete: (finalText) => {
      setMessages((prev) => [
        ...prev,
        { id: generateId(), role: "assistant", content: finalText },
      ]);
      setStreamEnabled(false);
      setStreamUrl("");
      lastSyncedTextRef.current = "";
      resetStream();
    },
    onError: () => {
      setStreamEnabled(false);
      setStreamUrl("");
      lastSyncedTextRef.current = "";
      resetStream();
    },
    onStateChange: (sseStreamState) => {
      // Sync SSE streaming tokens into the Zustand stream store incrementally
      if (sseStreamState.status === "streaming" && sseStreamState.partialText) {
        const newText = sseStreamState.partialText;
        const delta = newText.slice(lastSyncedTextRef.current.length);
        if (delta) {
          appendToken(delta);
          lastSyncedTextRef.current = newText;
        }
      }
    },
  });

  // Fix 1: Force copilot visible at xl+ (>=1280px) per AC
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1280 && !copilotVisible) {
        setCopilotVisible(true);
      }
    };
    window.addEventListener("resize", handleResize);
    handleResize(); // Check on mount
    return () => window.removeEventListener("resize", handleResize);
  }, [copilotVisible, setCopilotVisible]);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sseState]);

  const handleSubmit = async () => {
    const text = input.trim();
    if (!text) return;

    const userMsg: Message = {
      id: generateId(),
      role: "user",
      content: text,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    try {
      // POST user message to create a thread (avoids leaking content in URL/logs)
      resetStream();
      const res = await apiClient.post<{ thread_id: string }>("/copilot/message", { message: text, persona, route });
      setActiveThread(res.thread_id);
      // Connect SSE using the safe thread_id reference
      setStreamUrl(`/api/copilot/stream?thread_id=${res.thread_id}`);
      setStreamEnabled(true);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: generateId(), role: "assistant", content: "Sorry, something went wrong. Please try again." },
      ]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isStreaming =
    sseState.status === "connecting" || sseState.status === "streaming";
  const streamingText =
    sseState.status === "streaming" ? sseState.partialText : "";

  // Fix 3: On mobile (<lg), show as full-screen overlay when toggled.
  // On desktop (lg+), show as side panel. Hidden when copilotVisible is false.
  if (!copilotVisible) return null;

  return (
    <aside
      aria-label="AI Copilot panel"
      data-testid="copilot-panel"
      className={cn(
        "flex flex-col bg-card border-s border-border shrink-0",
        // Mobile: full-screen overlay
        "fixed inset-0 z-50",
        // Desktop (lg+): side panel
        "lg:relative lg:inset-auto lg:z-auto lg:h-full lg:w-[320px]",
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div>
          <h2 className="text-sm font-semibold text-foreground">{persona}</h2>
          <p className="text-xs text-muted-foreground">AI Copilot</p>
        </div>
        <button
          type="button"
          onClick={toggleCopilot}
          aria-label="Close AI Copilot panel"
          className="p-1.5 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto p-4 space-y-3"
        role="log"
        aria-label="Conversation history"
      >
        {messages.length === 0 && !isStreaming && (
          <div className="text-center text-muted-foreground text-sm py-8">
            <p className="font-medium mb-1">{persona}</p>
            <p className="text-xs">{prePrompt}</p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={[
              "rounded-lg px-3 py-2 text-sm",
              msg.role === "user"
                ? "bg-primary text-primary-foreground ms-8"
                : "bg-muted text-foreground me-8",
            ].join(" ")}
          >
            {msg.content}
          </div>
        ))}

        {/* Streaming response */}
        {isStreaming && (
          <div
            className="bg-muted text-foreground rounded-lg px-3 py-2 text-sm me-8"
            aria-live="polite"
            aria-atomic="false"
          >
            {streamingText || (
              <span className="text-muted-foreground animate-pulse">
                Thinking…
              </span>
            )}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Pre-loaded prompt suggestion */}
      {messages.length === 0 && !isStreaming && (
        <div className="px-4 pb-2">
          <button
            type="button"
            onClick={() => setInput(prePrompt)}
            className="w-full text-start text-xs text-muted-foreground bg-muted hover:bg-accent rounded-md px-3 py-2 transition-colors"
          >
            💡 {prePrompt}
          </button>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-border">
        {isStreaming && (
          <button
            type="button"
            onClick={() => { sseCancel(); resetStream(); }}
            className="w-full mb-2 text-xs text-destructive hover:underline"
          >
            Stop generating
          </button>
        )}
        <div className="flex gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            aria-label="Message AI Copilot"
            placeholder="Ask me anything…"
            rows={2}
            disabled={isStreaming}
            className="flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
          />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!input.trim() || isStreaming}
            aria-label="Send message"
            className="p-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            <Send className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </aside>
  );
}
