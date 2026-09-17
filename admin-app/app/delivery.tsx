import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, RefreshControl, ScrollView, Text, View } from "react-native";

import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { ListSkeleton } from "@/components/ui/Skeleton";
import { getDeliveryStats, type CategoryDeliveryRow } from "@/lib/api";

type Sort = "waiting" | "jobs" | "sent";

export default function DeliveryReportScreen() {
  const [days, setDays] = useState(7);
  const [sort, setSort] = useState<Sort>("waiting");
  const [onlyProblems, setOnlyProblems] = useState(false);

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["delivery-stats", days],
    queryFn: () => getDeliveryStats(days),
  });

  const rows = (data?.items ?? [])
    .filter((r) => (onlyProblems ? r.students_waiting > 0 || r.jobs_waiting_to_send > 0 : true))
    .sort((a, b) =>
      sort === "waiting"
        ? b.students_waiting - a.students_waiting
        : sort === "jobs"
          ? b.jobs - a.jobs
          : b.sent - a.sent
    );

  const totals = (data?.items ?? []).reduce(
    (acc, r) => ({
      jobs: acc.jobs + r.jobs,
      sent: acc.sent + r.sent,
      waiting: acc.waiting + r.students_waiting,
      held: acc.held + r.jobs_waiting_to_send,
    }),
    { jobs: 0, sent: 0, waiting: 0, held: 0 }
  );

  return (
    <ScrollView
      className="flex-1 bg-background"
      contentContainerStyle={{ padding: 16, paddingBottom: 40 }}
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={() => refetch()} />}
    >
      <View className="flex-row mb-1">
        {[7, 30].map((d) => (
          <Chip key={d} label={`Last ${d} days`} selected={days === d} onPress={() => setDays(d)} />
        ))}
        <Chip label="Only with issues" selected={onlyProblems} onPress={() => setOnlyProblems((v) => !v)} />
      </View>

      {isLoading || !data ? (
        <ListSkeleton />
      ) : (
        <>
          <Card className="mb-3">
            <View className="flex-row justify-between">
              <Total label="Jobs added" value={totals.jobs} />
              <Total label="Deliveries" value={totals.sent} />
              <Total label="Students waiting" value={totals.waiting} tone={totals.waiting > 0 ? "text-brand" : "text-ink"} />
              <Total label="On hold" value={totals.held} />
            </View>
            <Text className="text-xs text-muted mt-3">
              New jobs are held for {data.job_delay_minutes} min before sending. "Students waiting" have a ready job that
              will go out in the next digest.
            </Text>
          </Card>

          <View className="flex-row mb-2 items-center">
            <Text className="text-xs text-muted mr-2">Sort by</Text>
            <Chip label="Waiting" selected={sort === "waiting"} onPress={() => setSort("waiting")} />
            <Chip label="Jobs" selected={sort === "jobs"} onPress={() => setSort("jobs")} />
            <Chip label="Sent" selected={sort === "sent"} onPress={() => setSort("sent")} />
          </View>

          {rows.length === 0 ? (
            <Card>
              <Text className="text-muted text-center">Nothing to show for this filter.</Text>
            </Card>
          ) : (
            rows.map((r) => <CategoryRow key={r.category_id} row={r} />)
          )}
        </>
      )}
    </ScrollView>
  );
}

function Total({ label, value, tone = "text-ink" }: { label: string; value: number; tone?: string }) {
  return (
    <View className="items-center flex-1">
      <Text className={`text-xl font-bold ${tone}`}>{value.toLocaleString("en-IN")}</Text>
      <Text className="text-[11px] text-muted text-center mt-0.5">{label}</Text>
    </View>
  );
}

function CategoryRow({ row }: { row: CategoryDeliveryRow }) {
  const ctr = row.sent > 0 ? Math.round((row.clicked / row.sent) * 100) : 0;
  const warn = row.students_waiting > 0;
  return (
    <Pressable
      onPress={() => router.push({ pathname: "/(tabs)/jobs", params: { category_id: String(row.category_id) } })}
      className="bg-surface rounded-2xl px-4 py-3.5 mb-2 active:opacity-70"
    >
      <View className="flex-row items-center justify-between">
        <Text className="text-[16px] font-semibold text-ink flex-1" numberOfLines={1}>
          {row.name}
          {!row.is_active ? <Text className="text-muted"> (off)</Text> : null}
        </Text>
        {warn ? (
          <View className="bg-brand-soft rounded-full px-2.5 py-1">
            <Text className="text-brand text-xs font-semibold">{row.students_waiting} waiting</Text>
          </View>
        ) : null}
      </View>
      <View className="flex-row mt-2.5">
        <Stat label="Jobs" value={row.jobs} />
        <Stat label="On hold" value={row.jobs_waiting_to_send} />
        <Stat label="Subscribers" value={row.subscribers} />
        <Stat label="Sent" value={row.sent} />
        <Stat label="CTR" value={`${ctr}%`} />
      </View>
    </Pressable>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <View className="flex-1">
      <Text className="text-[15px] font-semibold text-ink">{value}</Text>
      <Text className="text-[11px] text-muted">{label}</Text>
    </View>
  );
}
