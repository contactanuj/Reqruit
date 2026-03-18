"use client";

// ErrorBoundary — Generic React error boundary with fallback UI (FE-4/FE-5)

import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Section name shown in the fallback UI */
  section?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Log to error reporting service (e.g. Sentry) in production
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          className="mx-auto max-w-md rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center"
        >
          <h2 className="mb-2 text-lg font-semibold text-destructive">
            Something went wrong
          </h2>
          <p className="mb-4 text-sm text-muted-foreground">
            {this.props.section
              ? `The ${this.props.section} section encountered an error.`
              : "An unexpected error occurred."}
          </p>
          <button
            type="button"
            onClick={this.handleReset}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
