import { Text, View } from "react-native";

/** iOS large-title header. */
export function ScreenHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <View className="px-4 pt-2 pb-3">
      <Text className="text-[32px] font-bold text-ink tracking-tight">{title}</Text>
      {subtitle ? <Text className="text-[15px] text-muted mt-0.5">{subtitle}</Text> : null}
    </View>
  );
}
