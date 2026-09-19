import * as Haptics from "expo-haptics";
import { MotiView } from "moti";
import { useState } from "react";
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
  const [pressed, setPressed] = useState(false);
  return (
    <MotiView
      animate={{ scale: pressed ? 0.94 : 1 }}
      transition={{ type: "spring", damping: 16, stiffness: 300 }}
      className="mr-2 mb-2"
    >
      <Pressable
        onPressIn={() => setPressed(true)}
        onPressOut={() => setPressed(false)}
        onPress={() => {
          Haptics.selectionAsync().catch(() => {});
          onPress?.();
        }}
        className={`rounded-full px-4 py-2 ${selected ? "bg-brand" : "bg-surface border border-line"}`}
      >
        <Text className={`text-[15px] font-semibold ${selected ? "text-white" : "text-ink"}`}>{label}</Text>
      </Pressable>
    </MotiView>
  );
}
