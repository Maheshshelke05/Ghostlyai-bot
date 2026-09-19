import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { getPublicSettings } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

function formatDate(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  });
}

const FEATURES = [
  { emoji: "⚡", label: "New jobs reach you within minutes, not once a day" },
  { emoji: "🔎", label: "Unlimited browsing across all your chosen categories" },
  { emoji: "🔔", label: "Push notifications the moment a matching job is posted" },
  { emoji: "✅", label: "Only verified jobs with official apply links" },
  { emoji: "💬", label: "Direct support chat with our team" },
];

export default function SubscriptionScreen() {
  const user = useAuthStore((s) => s.user);
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: getPublicSettings });

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["top", "bottom"]}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}>
        <Text className="font-display text-ink text-[24px] mb-4">Subscription</Text>

        <Card className={`mb-4 ${user?.has_access ? "bg-brand-soft" : "bg-accent-soft"}`}>
          {user?.has_access ? (
            <>
              <Text className="font-body-strong text-brand text-[15px]">
                {user.in_trial ? "Free trial active" : "Subscription active"}
              </Text>
              <Text className="text-ink text-[13px] mt-1">Valid until {formatDate(user.access_until)}</Text>
            </>
          ) : (
            <>
              <Text className="font-body-strong text-accent text-[15px]">Your access has expired</Text>
              <Text className="text-ink text-[13px] mt-1">
                Subscribe to keep getting job alerts for your categories.
              </Text>
            </>
          )}
        </Card>

        <Card className="mb-4">
          <Text className="font-heading text-ink text-[17px] mb-3">What's included</Text>
          <View className="gap-3">
            {FEATURES.map((f) => (
              <View key={f.label} className="flex-row items-start">
                <Text className="text-lg mr-2.5">{f.emoji}</Text>
                <Text className="flex-1 text-ink text-[14px] leading-5">{f.label}</Text>
              </View>
            ))}
          </View>
        </Card>

        <Card className="mb-6">
          <View className="flex-row items-baseline">
            <Text className="font-display text-ink text-[28px]">₹{settings?.price_inr ?? 99}</Text>
            <Text className="text-muted text-[14px] ml-1.5">/ {settings?.subscription_days ?? 30} days</Text>
          </View>
          <Text className="text-muted text-[13px] mt-1">
            {user?.in_trial ? "" : `New students get a ${settings?.trial_days ?? 3}-day free trial first.`}
          </Text>
        </Card>

        <Button
          label={user?.has_access ? "Renew / extend subscription" : `Subscribe — ₹${settings?.price_inr ?? 99}/${settings?.subscription_days ?? 30} days`}
          onPress={() => router.push("/payment/checkout")}
          variant="primary"
        />
      </ScrollView>
    </SafeAreaView>
  );
}
