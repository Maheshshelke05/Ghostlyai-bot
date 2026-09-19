import { Text, View } from "react-native";

import { Button } from "./Button";

export function EmptyState({
  emoji = "📭",
  title,
  actionLabel,
  onAction,
}: {
  emoji?: string;
  title: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <View className="items-center justify-center py-16 px-6">
      <Text className="text-5xl mb-3">{emoji}</Text>
      <Text className="text-center text-muted text-base mb-4">{title}</Text>
      {actionLabel && onAction ? (
        <View className="w-48">
          <Button label={actionLabel} onPress={onAction} variant="brand" />
        </View>
      ) : null}
    </View>
  );
}
