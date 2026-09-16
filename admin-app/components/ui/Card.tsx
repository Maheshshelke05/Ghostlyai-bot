import { Platform, View, type ViewProps } from "react-native";

const cardShadow = Platform.select({
  ios: { shadowColor: "#1E2420", shadowOpacity: 0.06, shadowRadius: 10, shadowOffset: { width: 0, height: 4 } },
  android: { elevation: 2 },
  default: {},
});

export function Card({ className = "", style, ...rest }: ViewProps & { className?: string }) {
  return (
    <View
      className={`rounded-[18px] bg-surface p-4 border border-line/60 dark:border-line/20 ${className}`}
      style={[cardShadow, style]}
      {...rest}
    />
  );
}
