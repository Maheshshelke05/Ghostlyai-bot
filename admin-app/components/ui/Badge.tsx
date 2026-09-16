import { Text, View } from "react-native";

type BadgeTone = "go" | "info" | "muted" | "danger" | "brand";

const TONE_CLASSES: Record<BadgeTone, string> = {
  go: "bg-go/15 text-go",
  info: "bg-info/15 text-info",
  muted: "bg-muted/15 text-muted",
  danger: "bg-danger/15 text-danger",
  brand: "bg-brand text-brand-ink",
};

export function Badge({ label, tone = "muted" }: { label: string; tone?: BadgeTone }) {
  const [bg, text] = TONE_CLASSES[tone].split(" ");
  return (
    <View className={`self-start rounded-full px-2.5 py-1 ${bg}`}>
      <Text className={`text-xs font-semibold ${text}`}>{label}</Text>
    </View>
  );
}

const ACCESS_BADGE: Record<string, { label: string; tone: BadgeTone }> = {
  paid: { label: "Paid", tone: "go" },
  trial: { label: "Trial", tone: "info" },
  none: { label: "Expired", tone: "muted" },
};

const STATUS_BADGE: Record<string, { label: string; tone: BadgeTone }> = {
  active: { label: "Active", tone: "go" },
  onboarding: { label: "Onboarding", tone: "info" },
  blocked: { label: "Blocked", tone: "danger" },
  bot_blocked: { label: "Bot blocked", tone: "danger" },
};

export function AccessBadge({ access }: { access: string }) {
  const cfg = ACCESS_BADGE[access] ?? { label: access, tone: "muted" as const };
  return <Badge label={cfg.label} tone={cfg.tone} />;
}

export function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_BADGE[status] ?? { label: status, tone: "muted" as const };
  return <Badge label={cfg.label} tone={cfg.tone} />;
}
