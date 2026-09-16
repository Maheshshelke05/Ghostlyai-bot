import { Pressable, Text } from "react-native";

export function Chip({
  label,
  selected,
  onPress,
}: {
  label: string;
  selected?: boolean;
  onPress?: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      className={`rounded-full px-4 py-2 mr-2 mb-2 border ${
        selected ? "bg-brand border-brand" : "bg-surface border-line"
      }`}
    >
      <Text className={`text-sm font-medium ${selected ? "text-brand-ink" : "text-ink"}`}>
        {label}
      </Text>
    </Pressable>
  );
}
