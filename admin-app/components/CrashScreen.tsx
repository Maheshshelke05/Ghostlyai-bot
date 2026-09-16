import * as Clipboard from "expo-clipboard";
import { useState } from "react";
import { ScrollView, Text, View } from "react-native";

import { Button } from "@/components/ui/Button";

interface Props {
  error: Error;
  componentStack?: string;
  onRestart: () => void;
}

export function CrashScreen({ error, componentStack, onRestart }: Props) {
  const [copied, setCopied] = useState(false);

  const details = [
    `Message: ${error.message}`,
    error.stack ? `\nStack:\n${error.stack}` : "",
    componentStack ? `\nComponent stack:${componentStack}` : "",
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <View className="flex-1 bg-background px-6 pt-16 pb-8">
      <Text className="text-4xl mb-3 text-center">⚠️</Text>
      <Text className="text-lg font-bold text-ink mb-2 text-center">App crash zala</Text>
      <Text className="text-sm text-muted mb-4 text-center">
        Khali cha detail "Copy" karun Mahesh la pathav - exact karan tyat aahe.
      </Text>

      <ScrollView className="flex-1 bg-surface border border-line rounded-2xl p-3 mb-4">
        <Text className="text-xs text-ink font-mono">{details}</Text>
      </ScrollView>

      <View className="gap-3">
        <Button
          label={copied ? "Copied!" : "Copy error details"}
          variant="ghost"
          onPress={async () => {
            await Clipboard.setStringAsync(details);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          }}
        />
        <Button label="Restart" variant="brand" onPress={onRestart} />
      </View>
    </View>
  );
}
