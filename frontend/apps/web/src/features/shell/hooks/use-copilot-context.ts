// use-copilot-context.ts — Route → AI Copilot persona mapping (FE-2.6)

"use client";

import { usePathname } from "next/navigation";

export interface CopilotContext {
  persona: string;
  prePrompt: string;
  /** The matched route prefix (e.g. "/jobs") or current pathname if no match. */
  route: string;
}

const CONTEXT_MAP: Record<string, CopilotContext> = {
  "/jobs": {
    persona: "Company Research Analyst",
    prePrompt:
      "Help me research this company — what's their culture, recent news, and typical interview process?",
  },
  "/interviews": {
    persona: "Interview Coach",
    prePrompt:
      "Help me prepare for my upcoming interview with tailored practice questions.",
  },
  "/offers": {
    persona: "Negotiation Advisor",
    prePrompt:
      "Help me evaluate this offer and craft a negotiation strategy to maximise my total compensation.",
  },
  "/applications": {
    persona: "Application Strategist",
    prePrompt:
      "Review my application pipeline and suggest prioritisation strategies.",
  },
  "/profile": {
    persona: "Profile Optimizer",
    prePrompt:
      "Analyse my profile and suggest improvements to maximise recruiter visibility.",
  },
  "/dashboard": {
    persona: "Career Advisor",
    prePrompt:
      "Give me an overview of my job search progress and suggest next steps.",
  },
};

const DEFAULT_CONTEXT: CopilotContext = {
  persona: "Career Advisor",
  prePrompt: "How can I help you with your job search today?",
};

export function useCopilotContext(): CopilotContext {
  const pathname = usePathname();

  // Match on prefix so nested routes work (e.g. /jobs/123)
  for (const [route, context] of Object.entries(CONTEXT_MAP)) {
    if (pathname === route || pathname.startsWith(`${route}/`)) {
      return { ...context, route };
    }
  }

  return { ...DEFAULT_CONTEXT, route: pathname };
}
