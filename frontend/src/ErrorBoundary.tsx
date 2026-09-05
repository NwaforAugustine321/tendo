import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode; // Optional custom fallback UI
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  // Catch the error and update state so the next render shows the fallback UI
  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  // Catch side-effects like logging errors to a monitoring service (Sentry, LogRocket, etc.)
  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(
      "Uncaught error captured by ErrorBoundary:",
      error,
      errorInfo,
    );
  }

  public render() {
    if (this.state.hasError) {
      // Return custom fallback UI or a default one
      return (
        this.props.fallback || (
          <div style={{ padding: "20px", textAlign: "center" }}>
            <h1>Something went wrong.</h1>
            <p>{this.state.error?.message}</p>
            <button onClick={() => window.location.reload()}>
              Reload Page
            </button>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
