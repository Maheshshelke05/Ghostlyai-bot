import { Text, View } from "react-native";

import { useCountUp } from "./useCountUp";

interface StatCardProps {
  label: string;
  value: number;
  icon?: string;
  format?: (n: number) => string;
  trend?: number; // positive = green chip, negative = red chip
}

export function StatCard({ label, value, icon, format, trend }: StatCardProps) {
  const animated = useCountUp(value);
  const display = format ? format(Math.round(animated)) : Math.round(animated).toLocaleString("en-IN");

  return (
    <View className="flex-1 min-w-[45%] rounded-[18px] bg-surface border border-line/60 dark:border-line/20 p-4">
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
      <Text className="mt-2 text-2xl font-extrabold text-ink dark:text-white">{display}</Text>
      <Text className="text-xs text-muted mt-0.5">{label}</Text>
    </View>
  );
}
