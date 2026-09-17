import * as Haptics from "expo-haptics";
import { MotiView } from "moti";
import { useState } from "react";
import { Platform, Pressable, Text, View } from "react-native";

import { useCountUp } from "./useCountUp";

const cardShadow = Platform.select({
  ios: { shadowColor: "#000000", shadowOpacity: 0.04, shadowRadius: 8, shadowOffset: { width: 0, height: 2 } },
  android: { elevation: 1 },
  default: {},
});

interface StatCardProps {
  label: string;
  value: number;
  icon?: string;
  format?: (n: number) => string;
  trend?: number; // positive = green chip, negative = red chip
  delay?: number;
  onPress?: () => void;
  highlight?: boolean; // tinted card for numbers that need attention
}

export function StatCard({ label, value, icon, format, trend, delay = 0, onPress, highlight }: StatCardProps) {
  const animated = useCountUp(value);
  const [pressed, setPressed] = useState(false);
  const display = format ? format(Math.round(animated)) : Math.round(animated).toLocaleString("en-IN");

  return (
    <MotiView
      from={{ opacity: 0, translateY: 10 }}
      animate={{ opacity: 1, translateY: 0, scale: pressed ? 0.97 : 1 }}
      transition={{ type: "spring", damping: 16, stiffness: 220, delay }}
      className="flex-1 min-w-[45%]"
    >
      <Pressable
        disabled={!onPress}
        onPressIn={() => setPressed(true)}
        onPressOut={() => setPressed(false)}
        onPress={() => {
          Haptics.selectionAsync().catch(() => {});
          onPress?.();
        }}
        className={`rounded-2xl p-4 ${highlight ? "bg-brand-soft" : "bg-surface"}`}
        style={cardShadow}
      >
        <View className="flex-row items-center justify-between">
          {icon ? <Text className="text-lg">{icon}</Text> : null}
          {trend !== undefined ? (
            <View className={`rounded-full px-2 py-0.5 ${trend >= 0 ? "bg-go/15" : "bg-danger/15"}`}>
              <Text className={`text-xs font-semibold ${trend >= 0 ? "text-go" : "text-danger"}`}>
                {trend >= 0 ? "+" : ""}
                {trend}%
              </Text>
            </View>
          ) : onPress ? (
            <Text className="text-line text-base">›</Text>
          ) : null}
        </View>
        <Text className={`mt-2 text-[26px] font-bold tracking-tight ${highlight ? "text-brand" : "text-ink"}`}>{display}</Text>
        <Text className="text-[13px] text-muted mt-0.5">{label}</Text>
      </Pressable>
    </MotiView>
  );
}
