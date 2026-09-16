import { Component, type ReactNode } from "react";
import { Text, View } from "react-native";

import { Button } from "@/components/ui/Button";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    console.error("Unhandled error in app tree:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <View className="flex-1 bg-background items-center justify-center px-6">
          <Text className="text-4xl mb-3">⚠️</Text>
          <Text className="text-lg font-bold text-ink mb-2 text-center">Kahi tari chukla</Text>
          <Text className="text-sm text-muted mb-6 text-center">{this.state.error.message}</Text>
          <Button label="Restart" variant="brand" fullWidth={false} onPress={() => this.setState({ error: null })} />
        </View>
      );
    }
    return this.props.children;
  }
}
