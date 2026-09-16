import { Component, type ReactNode } from "react";

import { CrashScreen } from "@/components/CrashScreen";
import { onCrash } from "@/lib/crashHandler";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
  componentStack?: string;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error("Unhandled error in app tree:", error, info.componentStack);
    this.setState({ componentStack: info.componentStack });
  }

  componentDidMount() {
    // Catches errors React's own boundary can't: async code, event handlers,
    // unhandled promise rejections - the most common real crash sources.
    onCrash((error, isFatal) => {
      if (isFatal) this.setState({ error });
    });
  }

  render() {
    if (this.state.error) {
      return (
        <CrashScreen
          error={this.state.error}
          componentStack={this.state.componentStack}
          onRestart={() => this.setState({ error: null, componentStack: undefined })}
        />
      );
    }
    return this.props.children;
  }
}
