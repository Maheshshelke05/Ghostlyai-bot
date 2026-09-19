import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { getCategories } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

function formatDate(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
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
            <View>
              <Text className="font-heading text-ink text-[18px]">{user?.full_name ?? "-"}</Text>
              <Text className="text-muted text-[14px]">{user?.phone ?? "-"}</Text>
            </View>
          </View>
          <View className="mt-3 pt-3 border-t border-line">
            <Text className="text-muted text-[13px]">District: {user?.district ?? "-"}</Text>
            {myCategoryNames.length > 0 ? (
              <Text className="text-muted text-[13px] mt-1">Categories: {myCategoryNames.join(", ")}</Text>
            ) : null}
          </View>
        </Card>

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
              <Text className="text-ink text-[13px] mt-1 mb-3">
                Subscribe to keep getting job alerts for your categories.
              </Text>
              <Button label="Subscribe — ₹99/30 days" onPress={() => router.push("/payment/checkout")} variant="primary" />
            </>
          )}
        </Card>

        {user?.has_access ? (
          <View className="mb-4">
            <Button label="Renew / extend subscription" onPress={() => router.push("/payment/checkout")} variant="ghost" />
          </View>
        ) : null}

        <Button label="Log out" onPress={logout} variant="ghost" />
      </ScrollView>
    </SafeAreaView>
  );
}
