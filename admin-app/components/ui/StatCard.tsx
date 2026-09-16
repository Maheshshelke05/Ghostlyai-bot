import { MotiView } from "moti";
import { Platform, Text, View } from "react-native";

import { useCountUp } from "./useCountUp";

const cardShadow = Platform.select({
  ios: { shadowColor: "#1E2420", shadowOpacity: 0.05, shadowRadius: 8, shadowOffset: { width: 0, height: 3 } },
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
}

export function StatCard({ label, value, icon, format, trend, delay = 0 }: StatCardProps) {
  const animated = useCountUp(value);
  const display = format ? format(Math.round(animated)) : Math.round(animated).toLocaleString("en-IN");

  return (
    <MotiView
      from={{ opacity: 0, translateY: 10 }}
      animate={{ opacity: 1, translateY: 0 }}
      transition={{ type: "timing", duration: 280, delay }}
      className="flex-1 min-w-[45%]"
    >
      <View
        className="rounded-[18px] bg-surface border border-line/60 p-4"
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
          ) : null}
        </View>
        <Text className="mt-2 text-2xl font-extrabold text-ink">{display}</Text>
        <Text className="text-xs text-muted mt-0.5">{label}</Text>
      </View>
    </MotiView>
  );
}
