import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { Pressable, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { getCategories } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

function Row({
  emoji,
  label,
  onPress,
  tone,
}: {
  emoji: string;
  label: string;
  onPress: () => void;
  tone?: "danger";
}) {
  return (
    <Pressable
      onPress={onPress}
      className="flex-row items-center bg-surface rounded-2xl px-4 py-4 mb-2.5 active:opacity-70"
    >
      <Text className="text-xl mr-3">{emoji}</Text>
      <Text className={`flex-1 font-body-strong text-[15px] ${tone === "danger" ? "text-danger" : "text-ink"}`}>
        {label}
      </Text>
      {tone === "danger" ? null : <Text className="text-muted text-lg">›</Text>}
    </Pressable>
  );
}

export default function ProfileScreen() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const { data: categories } = useQuery({ queryKey: ["categories"], queryFn: () => getCategories() });

  const myCategoryNames = (categories ?? [])
    .filter((c) => user?.category_ids.includes(c.id))
    .map((c) => c.name);

  return (
    <SafeAreaView className="flex-1 bg-background" edges={["top", "bottom"]}>
      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}>
        <Text className="font-display text-ink text-[24px] mb-4">Profile</Text>

        <Card className="mb-4">
          <View className="flex-row items-center mb-1">
            <View className="w-14 h-14 rounded-full bg-brand-soft items-center justify-center mr-3">
              <Text className="text-brand font-display text-xl">
                {(user?.full_name ?? "?").trim().charAt(0).toUpperCase()}
              </Text>
            </View>
            <View className="flex-1">
              <Text className="font-heading text-ink text-[18px]">{user?.full_name ?? "-"}</Text>
              <Text className="text-muted text-[14px]">{user?.phone ?? "-"}</Text>
              {user?.email ? <Text className="text-muted text-[13px]">{user.email}</Text> : null}
            </View>
          </View>
          {myCategoryNames.length > 0 ? (
            <View className="mt-3 pt-3 border-t border-line flex-row flex-wrap gap-1.5">
              {myCategoryNames.map((name) => (
                <Badge key={name} label={name} tone="muted" />
              ))}
            </View>
          ) : null}
        </Card>

        <Row emoji="💳" label="Subscription" onPress={() => router.push("/(tabs)/subscription")} />
        <Row emoji="💬" label="Support" onPress={() => router.push("/support")} />

        <View className="mt-4">
          <Row emoji="👻" label="About GhotlyAI" onPress={() => WebBrowser.openBrowserAsync("https://ghotlyai.in")} />
          <Row emoji="🔒" label="Privacy Policy" onPress={() => router.push("/privacy-policy")} />
          <Row emoji="📄" label="Terms & Conditions" onPress={() => router.push("/terms")} />
        </View>

        <View className="mt-4">
          <Row emoji="🚪" label="Log out" onPress={logout} tone="danger" />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
