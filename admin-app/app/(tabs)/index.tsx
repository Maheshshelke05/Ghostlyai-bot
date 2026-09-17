import { useQuery } from "@tanstack/react-query";
import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";
import { MotiView } from "moti";
import { BarChart } from "react-native-gifted-charts";
import { Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/ui/StatCard";
import { useCountUp } from "@/components/ui/useCountUp";
import { apiErrorMessage, getDashboard, getDeliveryStats, listSupportThreads } from "@/lib/api";
import { useAuthStore, useIsOwner } from "@/store/auth";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function DashboardScreen() {
  const admin = useAuthStore((s) => s.admin);
  const isOwner = useIsOwner();
  const insets = useSafeAreaInsets();
  const { data, isLoading, isError, error, refetch, isRefetching } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
    refetchInterval: 60_000,
  });
  // the two live "needs attention" numbers refresh on their own cadence
  const { data: support, refetch: refetchSupport } = useQuery({
    queryKey: ["support", "open", ""],
    queryFn: () => listSupportThreads({ status: "open", page: 1, size: 1 }),
    refetchInterval: 30_000,
    enabled: isOwner, // the inbox holds student phone numbers; the API only serves it to owners
  });
  const { data: delivery, refetch: refetchDelivery } = useQuery({
    queryKey: ["delivery-stats", 7],
    queryFn: () => getDeliveryStats(7),
    refetchInterval: 60_000,
  });

  const revenue = useCountUp(data?.revenue_inr.today ?? 0);

  const refreshAll = () => {
    refetch();
    refetchSupport();
    refetchDelivery();
  };

  if (isLoading) {
    return (
      <View className="flex-1 bg-background px-4" style={{ paddingTop: insets.top + 16 }}>
        <ListSkeleton count={4} />
      </View>
    );
  }

  if (isError || !data) {
    return (
      <View className="flex-1 bg-background items-center justify-center px-6">
        <Text className="text-muted text-center mb-4">
          {apiErrorMessage(error, "Couldn't load the dashboard. Check your internet connection.")}
        </Text>
        <Button label="Retry" onPress={() => refetch()} variant="brand" fullWidth={false} />
      </View>
    );
  }

  const openSupport = support?.total ?? 0;
  const studentsWaiting = delivery?.items.reduce((n, r) => n + r.students_waiting, 0) ?? 0;
  const jobsOnHold = delivery?.items.reduce((n, r) => n + r.jobs_waiting_to_send, 0) ?? 0;

  const chartData = data.last_7_days.map((d) => ({
    value: d.revenue_inr,
    label: d.date.slice(8, 10),
    frontColor: "#EA580C",
  }));

  return (
    <ScrollView
      className="flex-1 bg-background"
      contentContainerStyle={{ paddingTop: insets.top + 8, paddingBottom: 40 }}
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refreshAll} tintColor="#EA580C" />}
    >
      <MotiView
        from={{ opacity: 0, translateY: -6 }}
        animate={{ opacity: 1, translateY: 0 }}
        transition={{ type: "timing", duration: 300 }}
        className="px-4 pb-2"
      >
        <Text className="text-[15px] text-muted">{greeting()}</Text>
        <Text className="text-[32px] font-bold text-ink tracking-tight">{admin?.name ?? "Owner"} 👋</Text>
      </MotiView>

      <MotiView
        from={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ type: "timing", duration: 320 }}
        className="mx-4 mb-4"
      >
        <Pressable onPress={() => router.push("/(tabs)/payments")}>
          <LinearGradient
            colors={["#FB923C", "#EA580C"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={{ borderRadius: 20, padding: 20 }}
          >
            <Text className="text-white/85 text-[13px] font-semibold uppercase tracking-wide">Today's revenue</Text>
            <Text className="text-[40px] font-bold text-white mt-1 tracking-tight">
              ₹{Math.round(revenue).toLocaleString("en-IN")}
            </Text>
            <Text className="text-white/80 text-[13px] mt-1">
              This month ₹{data.revenue_inr.month.toLocaleString("en-IN")} · tap for payments
            </Text>
          </LinearGradient>
        </Pressable>
      </MotiView>

      {openSupport > 0 || studentsWaiting > 0 ? (
        <View className="flex-row flex-wrap gap-3 px-4 mb-3">
          {openSupport > 0 ? (
            <StatCard
              label="Support messages waiting for a reply"
              value={openSupport}
              icon="💬"
              highlight
              delay={20}
              onPress={() => router.push("/support")}
            />
          ) : null}
          {studentsWaiting > 0 ? (
            <StatCard
              label="Students with a job due in the next digest"
              value={studentsWaiting}
              icon="⏳"
              highlight
              delay={40}
              onPress={() => router.push("/delivery")}
            />
          ) : null}
        </View>
      ) : null}

      <View className="flex-row flex-wrap gap-3 px-4 mb-4">
        <StatCard label="Paid students" value={data.subscriptions.paid} icon="⭐" delay={60} onPress={() => router.push({ pathname: "/(tabs)/users", params: { filter: "paid" } })} />
        <StatCard label="On free trial" value={data.subscriptions.trial} icon="🎁" delay={90} onPress={() => router.push({ pathname: "/(tabs)/users", params: { filter: "trial" } })} />
        <StatCard label="New students today" value={data.users.new_today} icon="🆕" delay={120} onPress={() => router.push("/(tabs)/users")} />
        <StatCard label="Jobs added today" value={data.jobs.today} icon="💼" delay={150} onPress={() => router.push({ pathname: "/(tabs)/jobs", params: { filter: "today" } })} />
        <StatCard label="Jobs sent today" value={data.deliveries.sent_today} icon="📤" delay={180} onPress={() => router.push("/delivery")} />
        <StatCard
          label="Click rate today"
          value={data.deliveries.ctr_today * 100}
          format={(n) => `${n.toFixed(0)}%`}
          icon="👆"
          delay={210}
          onPress={() => router.push("/delivery")}
        />
      </View>

      {data.subscriptions.expiring_3_days > 0 ? (
        <Pressable
          onPress={() => router.push({ pathname: "/(tabs)/users", params: { expiring: "3" } })}
          className="mx-4 mb-4 rounded-2xl bg-surface p-4 flex-row items-center"
        >
          <Text className="text-2xl mr-3">⚠️</Text>
          <View className="flex-1">
            <Text className="text-ink font-semibold text-[16px]">
              {data.subscriptions.expiring_3_days} subscriptions expire in the next 3 days
            </Text>
            <Text className="text-muted text-[13px] mt-0.5">Tap to see who</Text>
          </View>
          <Text className="text-line text-lg">›</Text>
        </Pressable>
      ) : null}

      <Card className="mx-4 mb-4">
        <View className="flex-row items-center justify-between mb-3">
          <Text className="text-[17px] font-semibold text-ink">Revenue, last 7 days</Text>
          {jobsOnHold > 0 ? <Text className="text-xs text-muted">{jobsOnHold} jobs on hold</Text> : null}
        </View>
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
          yAxisTextStyle={{ color: "#8E8E93", fontSize: 11 }}
          xAxisLabelTextStyle={{ color: "#8E8E93", fontSize: 11 }}
        />
      </Card>

      <View className="px-4">
        <Text className="text-[17px] font-semibold text-ink mb-3">Quick actions</Text>
        <View className="flex-row flex-wrap gap-3">
          <View className="flex-1 min-w-[45%]">
            <Button label="➕ Add job" variant="primary" onPress={() => router.push("/jobs/new")} />
          </View>
          {isOwner ? (
            <View className="flex-1 min-w-[45%]">
              <Button label="📣 Broadcast" variant="brand" onPress={() => router.push("/broadcast")} />
            </View>
          ) : (
            <View className="flex-1 min-w-[45%]">
              <Button label="📥 Bulk upload" variant="brand" onPress={() => router.push("/jobs/new?tab=excel")} />
            </View>
          )}
          {isOwner ? (
            <View className="flex-1 min-w-[45%]">
              <Button label="💬 Support" variant="brand" onPress={() => router.push("/support")} />
            </View>
          ) : (
            <View className="flex-1 min-w-[45%]">
              <Button label="🗂 All jobs" variant="brand" onPress={() => router.push("/jobs")} />
            </View>
          )}
          <View className="flex-1 min-w-[45%]">
            <Button label="📊 Delivery report" variant="brand" onPress={() => router.push("/delivery")} />
          </View>
        </View>
      </View>
    </ScrollView>
  );
}
