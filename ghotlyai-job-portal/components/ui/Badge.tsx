import { Text, View } from "react-native";

type BadgeTone = "brand" | "info" | "muted" | "danger" | "accent";

const TONE_CLASSES: Record<BadgeTone, string> = {
  brand: "bg-brand-soft text-brand",
  info: "bg-info/15 text-info",
  muted: "bg-muted/15 text-muted",
  danger: "bg-danger/15 text-danger",
  accent: "bg-accent-soft text-accent",
};

export function Badge({ label, tone = "muted" }: { label: string; tone?: BadgeTone }) {
  const [bg, text] = TONE_CLASSES[tone].split(" ");
  return (
    <View className={`self-start rounded-full px-2.5 py-1 ${bg}`}>
      <Text className={`text-xs font-semibold ${text}`}>{label}</Text>
    </View>
  );
}
