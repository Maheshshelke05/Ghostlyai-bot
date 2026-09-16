import { Text, View } from "react-native";

export function ScreenHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <View className="px-4 pt-2 pb-3">
      <Text className="text-2xl font-extrabold text-ink dark:text-white">{title}</Text>
      {subtitle ? <Text className="text-sm text-muted mt-0.5">{subtitle}</Text> : null}
    </View>
  );
}
