import { useQuery } from "@tanstack/react-query";
import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";
import { MotiView } from "moti";
import { BarChart } from "react-native-gifted-charts";
import { Pressable, RefreshControl, ScrollView, Text, View } from "react-native";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/ui/StatCard";
import { useCountUp } from "@/components/ui/useCountUp";
import { apiErrorMessage, getDashboard } from "@/lib/api";
import { useAuthStore } from "@/store/auth";

export default function DashboardScreen() {
  const admin = useAuthStore((s) => s.admin);
  const { data, isLoading, isError, error, refetch, isRefetching } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
  });

  const revenue = useCountUp(data?.revenue_inr.today ?? 0);

  if (isLoading) {
    return (
      <View className="flex-1 bg-background pt-14 px-4">
        <ListSkeleton count={4} />
      </View>
    );
  }

  if (isError || !data) {
    return (
      <View className="flex-1 bg-background items-center justify-center px-6">
        <Text className="text-muted text-center mb-4">
          {apiErrorMessage(error, "Data load zala nahi. Internet check kara.")}
        </Text>
        <Button label="Retry" onPress={() => refetch()} variant="brand" fullWidth={false} />
      </View>
    );
  }

  const chartData = data.last_7_days.map((d) => ({
    value: d.revenue_inr,
    label: d.date.slice(8, 10),
    frontColor: "#F8CB46",
  }));

  return (
    <ScrollView
      className="flex-1 bg-background"
      contentContainerStyle={{ paddingBottom: 40 }}
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={() => refetch()} />}
    >
      <MotiView
        from={{ opacity: 0, translateY: -6 }}
        animate={{ opacity: 1, translateY: 0 }}
        transition={{ type: "timing", duration: 300 }}
        className="px-4 pt-14 pb-2"
      >
        <Text className="text-2xl font-extrabold text-ink">Namaskar, {admin?.name ?? "Owner"} 👋</Text>
        <Text className="text-muted text-sm mt-0.5">{new Date().toDateString()}</Text>
      </MotiView>

      <MotiView
        from={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "timing", duration: 320 }}
        className="mx-4 mb-4"
      >
        <LinearGradient
          colors={["#F8CB46", "#FFE08A"]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={{ borderRadius: 20, padding: 20 }}
        >
          <Text className="text-brand-ink/80 text-sm font-semibold">Aajchi kamai</Text>
          <Text className="text-4xl font-extrabold text-brand-ink mt-1">
            ₹{Math.round(revenue).toLocaleString("en-IN")}
          </Text>
          <Text className="text-brand-ink/70 text-xs mt-1">
            Ya mahinyachi ₹{data.revenue_inr.month.toLocaleString("en-IN")}
          </Text>
        </LinearGradient>
      </MotiView>

      <View className="flex-row flex-wrap gap-3 px-4 mb-4">
        <StatCard label="Paid users" value={data.subscriptions.paid} icon="⭐" delay={40} />
        <StatCard label="Trial users" value={data.subscriptions.trial} icon="🎁" delay={80} />
        <StatCard label="Aaj navin users" value={data.users.new_today} icon="🆕" delay={120} />
        <StatCard label="Aajche jobs" value={data.jobs.today} icon="💼" delay={160} />
        <StatCard label="Sent aaj" value={data.deliveries.sent_today} icon="📤" delay={200} />
        <StatCard
          label="Click rate"
          value={data.deliveries.ctr_today * 100}
          format={(n) => `${n.toFixed(0)}%`}
          icon="👆"
          delay={240}
        />
      </View>

      {data.subscriptions.expiring_3_days > 0 ? (
        <Pressable
          onPress={() => router.push({ pathname: "/(tabs)/users", params: { expiring: "3" } })}
          className="mx-4 mb-4 rounded-2xl bg-brand/40 border border-brand p-4"
        >
          <Text className="text-brand-ink font-semibold">
            ⚠️ {data.subscriptions.expiring_3_days} subscriptions 3 divsat sampnar
          </Text>
          <Text className="text-brand-ink/70 text-xs mt-0.5">Tap to see users</Text>
        </Pressable>
      ) : null}

      <Card className="mx-4 mb-4">
        <Text className="text-base font-bold text-ink mb-3">Last 7 days revenue</Text>
        <BarChart
          data={chartData}
          barWidth={22}
          spacing={18}
          roundedTop
          hideRules
          xAxisThickness={0}
          yAxisThickness={0}
          noOfSections={3}
          height={140}
        />
      </Card>

      <View className="px-4">
        <Text className="text-base font-bold text-ink mb-3">Quick actions</Text>
        <View className="flex-row flex-wrap gap-3">
          <View className="flex-1 min-w-[45%]">
            <Button label="➕ Job add" variant="brand" onPress={() => router.push("/jobs/new")} />
          </View>
          <View className="flex-1 min-w-[45%]">
            <Button label="📣 Broadcast" variant="ghost" onPress={() => router.push("/broadcast")} />
          </View>
        </View>
      </View>
    </ScrollView>
  );
}
