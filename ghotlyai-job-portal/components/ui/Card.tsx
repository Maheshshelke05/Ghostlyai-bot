import { Platform, View, type ViewProps } from "react-native";

// iOS inset-grouped card: white on the grey grouped background, no hard border,
// just a whisper of shadow so it reads as a raised surface.
const cardShadow = Platform.select({
  ios: { shadowColor: "#000000", shadowOpacity: 0.04, shadowRadius: 8, shadowOffset: { width: 0, height: 2 } },
  android: { elevation: 1 },
  default: {},
});

export function Card({ className = "", style, ...rest }: ViewProps & { className?: string }) {
  return <View className={`rounded-2xl bg-surface p-4 ${className}`} style={[cardShadow, style]} {...rest} />;
}
